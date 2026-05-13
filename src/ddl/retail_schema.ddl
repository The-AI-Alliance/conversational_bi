-- ============================================================
-- Bike Sales Model - AWS Athena DDL
-- Generated from: Bike Sales Model.json
-- ============================================================

CREATE DATABASE IF NOT EXISTS retail_decision_support_demo;

-- ------------------------------------------------------------
-- SalesOrderItems
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.SalesOrderItems (
    SALESORDERID       VARCHAR(10)    COMMENT 'Sales order ID (PK)',
    SALESORDERITEM     VARCHAR(10)    COMMENT 'Sales order item (PK)',
    PRODUCTID          VARCHAR(10)    COMMENT 'Product ID',
    NOTEID             VARCHAR(10)    COMMENT 'Note ID',
    CURRENCY           VARCHAR(5)     COMMENT 'Currency key',
    GROSSAMOUNT        DECIMAL(15,2)  COMMENT 'Gross amount',
    NETAMOUNT          DECIMAL(15,2)  COMMENT 'Net amount',
    TAXAMOUNT          DECIMAL(15,2)  COMMENT 'Tax amount',
    ITEMATPSTATUS      VARCHAR(1)     COMMENT 'Item available to promise status',
    OPITEMPOS          VARCHAR(10)    COMMENT 'Open Item',
    QUANTITY           DECIMAL(13,3)  COMMENT 'Quantity',
    QUANTITYUNIT       VARCHAR(3)     COMMENT 'Quantity unit',
    DELIVERYDATE       VARCHAR(8)     COMMENT 'Delivery date in YYYYMMDD format'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/salesorderitems/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- SalesOrders
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.SalesOrders (
    SALESORDERID       VARCHAR(10)    COMMENT 'Sales order ID (PK)',
    CREATEDBY          VARCHAR(10)    COMMENT 'Created by',
    CREATEDAT          VARCHAR(8)     COMMENT 'Created at date in YYYYMMDD format',
    CHANGEDBY          VARCHAR(10)    COMMENT 'Changed by',
    CHANGEDAT          VARCHAR(8)     COMMENT 'Changed at date in YYYYMMDD format',
    FISCVARIANT        VARCHAR(2)     COMMENT 'Fiscal year variant',
    FISCALYEARPERIOD   VARCHAR(7)     COMMENT 'Fiscal year period',
    NOTEID             VARCHAR(10)    COMMENT 'Note ID',
    PARTNERID          VARCHAR(10)    COMMENT 'Partner ID',
    SALESORG           VARCHAR(4)     COMMENT 'Sales organisation',
    CURRENCY           VARCHAR(5)     COMMENT 'Currency key',
    GROSSAMOUNT        DECIMAL(15,2)  COMMENT 'Gross amount',
    NETAMOUNT          DECIMAL(15,2)  COMMENT 'Net amount',
    TAXAMOUNT          DECIMAL(15,2)  COMMENT 'Tax amount',
    LIFECYCLESTATUS    VARCHAR(1)     COMMENT 'Life cycle status',
    BILLINGSTATUS      VARCHAR(1)     COMMENT 'Billing status',
    DELIVERYSTATUS     VARCHAR(1)     COMMENT 'Delivery status'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/salesorders/'
TBLPROPERTIES ('skip.header.line.count'='1')
-- ------------------------------------------------------------
-- Addresses
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.Addresses (
    ADDRESSID           VARCHAR(10)    COMMENT 'Address ID (PK)',
    CITY                VARCHAR(40)    COMMENT 'City',
    POSTALCODE          VARCHAR(10)    COMMENT 'Postal code',
    STREET              VARCHAR(60)    COMMENT 'Street',
    BUILDING            VARCHAR(10)    COMMENT 'Building',
    COUNTRY             VARCHAR(3)     COMMENT 'Country',
    REGION              VARCHAR(4)     COMMENT 'Region',
    ADDRESSTYPE         VARCHAR(2)     COMMENT 'Address type',
    VALIDITY_STARTDATE  VARCHAR(8)     COMMENT 'Validity start date YYYYMMDD format',
    VALIDITY_ENDDATE    VARCHAR(8)     COMMENT 'Validity end date YYYYMMDD format',
    LATITUDE            DOUBLE         COMMENT 'Latitude',
    LONGITUDE           DOUBLE         COMMENT 'Longitude'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/addresses/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- BusinessPartners
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.BusinessPartners (
    PARTNERID          VARCHAR(10)    COMMENT 'Partner ID (PK)',
    PARTNERROLE        VARCHAR(3)     COMMENT 'Partner role',
    EMAILADDRESS       VARCHAR(255)   COMMENT 'Email address',
    PHONENUMBER        VARCHAR(30)    COMMENT 'Phone number',
    FAXNUMBER          VARCHAR(30)    COMMENT 'Fax number',
    WEBADDRESS         VARCHAR(1024)  COMMENT 'Web address',
    ADDRESSID          VARCHAR(10)    COMMENT 'Address ID',
    COMPANYNAME        VARCHAR(80)    COMMENT 'Company name',
    LEGALFORM          VARCHAR(10)    COMMENT 'Legal form',
    CREATEDBY          VARCHAR(10)    COMMENT 'Created by',
    CREATEDAT          VARCHAR(8)     COMMENT 'Created at date in YYYYMMDD format',
    CHANGEDBY          VARCHAR(10)    COMMENT 'Changed by',
    CHANGEDAT          VARCHAR(8)     COMMENT 'Changed at date in YYYYMMDD format',
    CURRENCY           VARCHAR(5)     COMMENT 'Currency key'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/businesspartners/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- Employees
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.Employees (
    EMPLOYEEID          VARCHAR(10)    COMMENT 'Employee ID (PK)',
    NAME_FIRST          VARCHAR(40)    COMMENT 'First name',
    NAME_MIDDLE         VARCHAR(40)    COMMENT 'Middle name',
    NAME_LAST           VARCHAR(40)    COMMENT 'Last name',
    NAME_INITIALS       VARCHAR(10)    COMMENT 'Name initials',
    SEX                 VARCHAR(1)     COMMENT 'Sex',
    LANGUAGE            VARCHAR(2)     COMMENT 'Language',
    PHONENUMBER         VARCHAR(30)    COMMENT 'Phone number',
    EMAILADDRESS        VARCHAR(255)   COMMENT 'Email address',
    LOGINNAME           VARCHAR(12)    COMMENT 'Login name',
    ADDRESSID           VARCHAR(10)    COMMENT 'Address ID',
    VALIDITY_STARTDATE  VARCHAR(8)     COMMENT 'Valid starting from date, stored as an string YYYYMMDD',
    VALIDITY_ENDDATE    VARCHAR(8)     COMMENT 'Valid ending at date, stored as an string YYYYMMDD'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/employees/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- ProductCategories
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.ProductCategories (
    PRODCATEGORYID     VARCHAR(2)     COMMENT 'Product category ID (PK)',
    CREATEDBY          VARCHAR(10)    COMMENT 'Created by',
    CREATEDAT          VARCHAR(8)     COMMENT 'Created at date, stored as an string YYYYMMDD'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/productcategories/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- ProductCategoryText
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.ProductCategoryText (
    PRODCATEGORYID     VARCHAR(2)     COMMENT 'Product category ID (PK)',
    LANGUAGE           VARCHAR(2)     COMMENT 'Language (PK)',
    SHORT_DESCR        VARCHAR(20)    COMMENT 'Short description',
    MEDIUM_DESCR       VARCHAR(40)    COMMENT 'Medium description',
    LONG_DESCR         VARCHAR(10)    COMMENT 'Long description'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/productcategorytext/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- Products
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.Products (
    PRODUCTID           VARCHAR(10)    COMMENT 'Product ID (PK)',
    TYPECODE            VARCHAR(2)     COMMENT 'Type code',
    PRODCATEGORYID      VARCHAR(2)     COMMENT 'Product category ID',
    CREATEDBY           VARCHAR(10)    COMMENT 'Created by',
    CREATEDAT           VARCHAR(8)     COMMENT 'Created at date, stored as an string YYYYMMDD',
    CHANGEDBY           VARCHAR(10)    COMMENT 'Changed by',
    CHANGEDAT           VARCHAR(8)     COMMENT 'Changed at date, stored as an string YYYYMMDD',
    SUPPLIER_PARTNERID  VARCHAR(10)    COMMENT 'Supplier partner ID',
    TAXTARIFFCODE       INT            COMMENT 'Tax tariff code',
    QUANTITYUNIT        VARCHAR(3)     COMMENT 'Quantity unit',
    WEIGHTMEASURE       DECIMAL(13,3)  COMMENT 'Weight measure',
    WEIGHTUNIT          VARCHAR(3)     COMMENT 'Weight unit',
    CURRENCY            VARCHAR(5)     COMMENT 'Currency key',
    PRICE               DECIMAL(15,2)  COMMENT 'Price',
    WIDTH               DECIMAL(13,3)  COMMENT 'Width',
    DEPTH               DECIMAL(13,3)  COMMENT 'Depth',
    HEIGHT              DECIMAL(13,3)  COMMENT 'Height',
    DIMENSIONUNIT       VARCHAR(3)     COMMENT 'Dimension unit',
    PRODUCTPICURL       VARCHAR(255)   COMMENT 'Product picture URL'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/products/'
TBLPROPERTIES ('skip.header.line.count'='1')

-- ------------------------------------------------------------
-- ProductTexts
-- ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS retail_decision_support_demo.ProductTexts (
    PRODUCTID          VARCHAR(10)    COMMENT 'Product ID (PK)',
    LANGUAGE           VARCHAR(2)     COMMENT 'Language (PK)',
    SHORT_DESCR        VARCHAR(20)    COMMENT 'Short description',
    MEDIUM_DESCR       VARCHAR(40)    COMMENT 'Medium description',
    LONG_DESCR         VARCHAR(10)    COMMENT 'Long description'
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://<replace with app_ci variable from ./iac/aws/iac/app.py>-datalake-dev-us-east-2/bike_sales/producttexts/'
TBLPROPERTIES ('skip.header.line.count'='1')