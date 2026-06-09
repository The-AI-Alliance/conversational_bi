-- Retail Electronics Ontology - DDL
-- Generated from ontology_analysis.ipynb

CREATE EXTERNAL TABLE IF NOT EXISTS dim_product_family (
    family_id       STRING,
    family_code     STRING,
    family_name     STRING,
    sei_grupo       STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('serialization.format' = ',', 'field.delim' = ',')
STORED AS TEXTFILE
LOCATION 's3://retail-electronics/dimensions/dim_product_family/';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_product_subfamily (
    subfamily_id    STRING,
    family_id       STRING,
    subfamily_code  STRING,
    subfamily_name  STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('serialization.format' = ',', 'field.delim' = ',')
STORED AS TEXTFILE
LOCATION 's3://retail-electronics/dimensions/dim_product_subfamily/';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_product_type (
    product_type_id     STRING,
    subfamily_id        STRING,
    product_type_name   STRING,
    source              STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('serialization.format' = ',', 'field.delim' = ',')
STORED AS TEXTFILE
LOCATION 's3://retail-electronics/dimensions/dim_product_type/';

CREATE EXTERNAL TABLE IF NOT EXISTS bridge_sku_taxonomy (
    item_code           STRING,
    product_type_id     STRING,
    is_sold             STRING,
    mapping_source      STRING,
    needs_review        STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('serialization.format' = ',', 'field.delim' = ',')
STORED AS TEXTFILE
LOCATION 's3://retail-electronics/dimensions/bridge_sku_taxonomy/';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_temporal (
    season_code     STRING,
    season_name     STRING,
    year_start      STRING,
    year_end        STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('serialization.format' = ',', 'field.delim' = ',')
STORED AS TEXTFILE
LOCATION 's3://retail-electronics/dimensions/dim_temporal/';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_organization (
    org_id          STRING,
    level1          STRING,
    level2          STRING,
    level3          STRING,
    area_negocio    STRING,
    departamento    STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('serialization.format' = ',', 'field.delim' = ',')
STORED AS TEXTFILE
LOCATION 's3://retail-electronics/dimensions/dim_organization/';
