"""
Kafka Producer — Real-Time Prescription Claim Events
In production this would sit inside the pharmacy claims adjudication system
and publish one event per processed claim. Here it's the ingestion entry
point for anything that can't wait for the nightly batch DAG — e.g. live
opioid-overutilization alerting, real-time cost-spike detection.

Topic: healthcare.claims.raw
Partition key: prscrbr_state_abrvtn (co-locates a state's claims on one
partition so a downstream per-state windowed aggregation stays ordered).
"""

import json
import logging
import os
from datetime import datetime, timezone
from confluent_kafka import Producer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClaimEventProducer")

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CLAIMS_TOPIC = "healthcare.claims.raw"


def _delivery_callback(err, msg):
    if err is not None:
        logger.error(f"Delivery failed for record {msg.key()}: {err}")
    else:
        logger.debug(f"Delivered to {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()}")


class ClaimEventProducer:
    """Thin wrapper around confluent-kafka Producer with schema validation + retries."""

    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",              # wait for all in-sync replicas — no silent data loss
            "retries": 5,
            "retry.backoff.ms": 200,
            "enable.idempotence": True,  # prevents duplicate delivery on retry (exactly-once producer semantics)
            "compression.type": "snappy",
        })

    def publish_claim(self, claim: dict):
        """
        Publishes a single claim event. Expected schema (see schemas/claim_event_schema.py):
        {prscrbr_npi, prscrbr_state_abrvtn, gnrc_name, brnd_name, drug_cost_usd,
         is_opioid, claim_timestamp}
        """
        from schemas.claim_event_schema import validate_claim_event

        errors = validate_claim_event(claim)
        if errors:
            raise ValueError(f"Invalid claim event, refusing to publish: {errors}")

        claim["_produced_at"] = datetime.now(timezone.utc).isoformat()
        partition_key = claim["prscrbr_state_abrvtn"]

        self.producer.produce(
            topic=CLAIMS_TOPIC,
            key=partition_key.encode("utf-8"),
            value=json.dumps(claim).encode("utf-8"),
            callback=_delivery_callback,
        )
        self.producer.poll(0)  # trigger delivery callbacks without blocking

    def flush(self, timeout: float = 10.0):
        """Call before shutdown to ensure all buffered events are actually sent."""
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages still undelivered after flush timeout")


if __name__ == "__main__":
    # Demo: publish a handful of synthetic claim events (for local testing without
    # a real claims-adjudication system upstream).
    import random
    import time

    producer = ClaimEventProducer()
    states = ["TX", "CA", "FL", "NY", "PA"]
    drugs = [("OXYCODONE", "OXY-BRAND", True), ("IBUPROFEN", "ADVIL", False), ("METFORMIN", "GLUCOPHAGE", False)]

    for i in range(20):
        drug = random.choice(drugs)
        claim = {
            "claim_id": f"demo-{i}",
            "prscrbr_npi": random.randint(1000000000, 1999999999),
            "prscrbr_state_abrvtn": random.choice(states),
            "gnrc_name": drug[0],
            "brnd_name": drug[1],
            "is_opioid": drug[2],
            "drug_cost_usd": round(random.uniform(5, 500), 2),
            "claim_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        producer.publish_claim(claim)
        logger.info(f"Published claim {i}: {claim['gnrc_name']} in {claim['prscrbr_state_abrvtn']}")
        time.sleep(0.2)

    producer.flush()
    logger.info("Demo publish complete")
