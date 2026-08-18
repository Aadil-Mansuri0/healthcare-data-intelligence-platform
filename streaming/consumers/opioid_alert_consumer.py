"""
Kafka Consumer — Real-Time Opioid Overutilization Alerting
Consumes claim events and maintains a sliding 1-hour window of opioid claim
counts per prescriber. If a prescriber crosses a threshold within the window,
fires an alert immediately — this is the "can't wait for the nightly batch"
use case streaming exists for for this platform (CMS's Overutilization
Monitoring System referenced in rag/knowledge_base/documents.py works
similarly, at daily granularity; this gives sub-minute detection).

Also writes every consumed event to S3 as a raw streaming-bronze landing
zone (Parquet, hourly-partitioned) so the batch Medallion pipeline can pick
up the same data downstream without a separate ingestion path.
"""

import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from confluent_kafka import Consumer, KafkaError

from streaming.schemas.claim_event_schema import validate_claim_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OpioidAlertConsumer")

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CLAIMS_TOPIC = "healthcare.claims.raw"
ALERTS_TOPIC = "healthcare.alerts.opioid"

WINDOW_MINUTES = 60
OPIOID_CLAIM_THRESHOLD = 15   # claims by a single prescriber within the window


class SlidingWindowTracker:
    """Per-prescriber sliding window of opioid claim timestamps."""

    def __init__(self, window_minutes: int = WINDOW_MINUTES):
        self.window = timedelta(minutes=window_minutes)
        self._events: dict[int, deque] = defaultdict(deque)

    def record(self, prscrbr_npi: int, ts: datetime) -> int:
        """Records an opioid claim and returns the current count within the window."""
        events = self._events[prscrbr_npi]
        events.append(ts)
        self._evict_stale(events, ts)
        return len(events)

    def _evict_stale(self, events: deque, now: datetime):
        cutoff = now - self.window
        while events and events[0] < cutoff:
            events.popleft()


def _write_to_streaming_bronze(claim: dict):
    """
    Lands the raw event into S3 under a streaming-specific prefix, partitioned
    by hour, so the batch pipeline's Bronze layer can union this with the
    nightly PostgreSQL bulk load without double-counting (dedup happens in
    Silver via the existing dropDuplicates on business keys).
    """
    # In production: buffer events in-memory and flush to S3 every N seconds/events
    # via a small Parquet writer (e.g. pyarrow), rather than one S3 PUT per event.
    # Sketch only — full buffering implementation omitted for brevity.
    hour_partition = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    logger.debug(f"Would land claim {claim['claim_id']} to s3://healthcare-datalake/bronze_streaming/date_hour={hour_partition}/")


def _publish_alert(producer, prescriber_npi: int, state: str, claim_count: int):
    """Publishes an overutilization alert event for downstream consumers (Slack bot, dashboard)."""
    alert = {
        "alert_type": "opioid_overutilization",
        "prscrbr_npi": prescriber_npi,
        "prscrbr_state_abrvtn": state,
        "claim_count_in_window": claim_count,
        "window_minutes": WINDOW_MINUTES,
        "threshold": OPIOID_CLAIM_THRESHOLD,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "severity": "high" if claim_count > OPIOID_CLAIM_THRESHOLD * 1.5 else "medium",
    }
    producer.produce(
        topic=ALERTS_TOPIC,
        key=str(prescriber_npi).encode("utf-8"),
        value=json.dumps(alert).encode("utf-8"),
    )
    producer.poll(0)
    logger.warning(f"🚨 ALERT: prescriber {prescriber_npi} ({state}) — {claim_count} opioid claims in {WINDOW_MINUTES}min window")


def run_consumer():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "opioid-alerting-consumer-group",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,   # manual commit after successful processing — at-least-once delivery
    })
    consumer.subscribe([CLAIMS_TOPIC])

    from confluent_kafka import Producer
    alert_producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    tracker = SlidingWindowTracker()

    logger.info(f"Listening on '{CLAIMS_TOPIC}' — opioid threshold: {OPIOID_CLAIM_THRESHOLD}/{WINDOW_MINUTES}min")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Consumer error: {msg.error()}")
                continue

            try:
                claim = json.loads(msg.value().decode("utf-8"))
            except json.JSONDecodeError:
                logger.error(f"Skipping malformed message at offset {msg.offset()}")
                consumer.commit(msg)
                continue

            errors = validate_claim_event(claim)
            if errors:
                logger.warning(f"Skipping invalid claim event: {errors}")
                consumer.commit(msg)
                continue

            _write_to_streaming_bronze(claim)

            if claim.get("is_opioid"):
                ts = datetime.fromisoformat(claim["claim_timestamp"].replace("Z", "+00:00"))
                count = tracker.record(claim["prscrbr_npi"], ts)
                if count >= OPIOID_CLAIM_THRESHOLD:
                    _publish_alert(alert_producer, claim["prscrbr_npi"], claim["prscrbr_state_abrvtn"], count)

            consumer.commit(msg)  # commit only after successful processing

    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        consumer.close()
        alert_producer.flush()


if __name__ == "__main__":
    run_consumer()
