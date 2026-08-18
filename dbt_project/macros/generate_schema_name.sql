{#
    Overrides dbt's default schema-naming behavior so models materialize into
    the exact GOLD_SCHEMA/staging schema names this project already uses in
    Snowflake (scripts/snowflake_setup.sql), rather than dbt's default of
    concatenating "<target_schema>_<custom_schema>".
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
