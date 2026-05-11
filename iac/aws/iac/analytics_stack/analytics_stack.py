from aws_cdk import aws_s3 as s3, aws_glue as glue, aws_athena as athena, Stack

from constructs import Construct


class AnalyticsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        tag: str,
        env: str,
        datalake_bucket_name: str,
        demo_dataset_name: str,
        db_name: str,
        application_ci: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        if len(tag) > 0:
            tag = tag[:-1]

        # Reference existing S3 bucket for Athena data
        datalake_bucket = s3.Bucket.from_bucket_name(
            self, id=f"{application_ci}DatalakeBucket", bucket_name=datalake_bucket_name
        )

        athena_catalog_name = "AwsDataCatalog"
        # Create a Glue database for Athena
        glue_db = glue.CfnDatabase(
            self, db_name, catalog_id=self.account, database_input={"name": db_name}
        )

        # Athena table definition for ProductCategories table
        product_categories_table = glue.CfnTable(
            self,
            "ProductCategoriesTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "productcategories",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "productcategoryid", "type": "string"},
                        {"name": "createdby", "type": "string"},
                        {"name": "createdat", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/productcategories/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        product_categories_table.add_dependency(glue_db)

        # Athena table definition for ProductCategoryText table
        product_category_text = glue.CfnTable(
            self,
            "ProductCategoryTextTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "productcategorytext",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "prodcategoryid", "type": "string"},
                        {"name": "language", "type": "string"},
                        {"name": "short_descr", "type": "string"},
                        {"name": "medium_descr", "type": "string"},
                        {"name": "long_descr", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/productcategorytext/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        product_category_text.add_dependency(glue_db)

        # Athena table definition for Products table
        products = glue.CfnTable(
            self,
            "ProductsTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "products",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "productid", "type": "string"},
                        {"name": "typecode", "type": "string"},
                        {"name": "productcategoryid", "type": "string"},
                        {"name": "createdby", "type": "string"},
                        {"name": "createdat", "type": "string"},
                        {"name": "changedby ", "type": "string"},
                        {"name": "changedat", "type": "string"},
                        {"name": "supplier_partnerid", "type": "string"},
                        {"name": "taxtariffcode", "type": "int"},
                        {"name": "quantityunit", "type": "string"},
                        {"name": "weightmeasure", "type": "double"},
                        {"name": "weightunit", "type": "string"},
                        {"name": "currency", "type": "string"},
                        {"name": "price", "type": "double"},
                        {"name": "width", "type": "string"},
                        {"name": "depth", "type": "string"},
                        {"name": "height", "type": "string"},
                        {"name": "dimensionunit", "type": "string"},
                        {"name": "productpicurl", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/products/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        products.add_dependency(glue_db)

        # Athena table definition for ProductTexts table
        product_texts = glue.CfnTable(
            self,
            "ProductTextsTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "producttexts",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "productid", "type": "string"},
                        {"name": "language", "type": "string"},
                        {"name": "short_descr", "type": "string"},
                        {"name": "medium_descr", "type": "string"},
                        {"name": "long_descr", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/producttexts/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        product_texts.add_dependency(glue_db)

        # Athena table definition for Employees table
        employees = glue.CfnTable(
            self,
            "EmployeesTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "employees",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "employeeid", "type": "string"},
                        {"name": "name_first", "type": "string"},
                        {"name": "name_middle", "type": "string"},
                        {"name": "name_last", "type": "string"},
                        {"name": "name_initials", "type": "string"},
                        {"name": "sex", "type": "string"},
                        {"name": "language", "type": "string"},
                        {"name": "phonenumber", "type": "string"},
                        {"name": "emailaddress", "type": "string"},
                        {"name": "loginname", "type": "string"},
                        {"name": "addressid", "type": "string"},
                        {"name": "validity_startdate", "type": "string"},
                        {"name": "validity_enddate", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/employees/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        employees.add_dependency(glue_db)

        # Athena table definition for BusinessPartners table
        business_partners = glue.CfnTable(
            self,
            "BusinessPartnersTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "businesspartners",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "partnerid", "type": "string"},
                        {"name": "partnerrole", "type": "string"},
                        {"name": "emailaddress", "type": "string"},
                        {"name": "phonenumber", "type": "string"},
                        {"name": "faxnumber", "type": "string"},
                        {"name": "webaddress", "type": "string"},
                        {"name": "addressid", "type": "string"},
                        {"name": "companyname", "type": "string"},
                        {"name": "legalform", "type": "string"},
                        {"name": "createdby", "type": "string"},
                        {"name": "createdat", "type": "string"},
                        {"name": "changedby", "type": "string"},
                        {"name": "changedat", "type": "string"},
                        {"name": "currency", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/businesspartners/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        business_partners.add_dependency(glue_db)

        # Athena table definition for Addresses table
        addresses = glue.CfnTable(
            self,
            "AddressesTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "addresses",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "addressid", "type": "string"},
                        {"name": "city", "type": "string"},
                        {"name": "postalcode", "type": "string"},
                        {"name": "street", "type": "string"},
                        {"name": "building", "type": "string"},
                        {"name": "country", "type": "string"},
                        {"name": "region", "type": "string"},
                        {"name": "addresstype", "type": "string"},
                        {"name": "validity_startdate", "type": "string"},
                        {"name": "validity_enddate", "type": "string"},
                        {"name": "latitude", "type": "double"},
                        {"name": "longitude", "type": "double"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/addresses/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        addresses.add_dependency(glue_db)

        # Athena table definition for SalesOrders table
        sales_orders = glue.CfnTable(
            self,
            "SalesOrdersTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "salesorders",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "salesorderid", "type": "string"},
                        {"name": "createdby", "type": "string"},
                        {"name": "createdat", "type": "string"},
                        {"name": "changedby", "type": "string"},
                        {"name": "changedat", "type": "string"},
                        {"name": "fiscvariant", "type": "string"},
                        {"name": "fiscalyearperiod", "type": "string"},
                        {"name": "noteid", "type": "string"},
                        {"name": "partnerid", "type": "string"},
                        {"name": "salesorg", "type": "string"},
                        {"name": "currency", "type": "string"},
                        {"name": "grossamount", "type": "double"},
                        {"name": "netamount", "type": "double"},
                        {"name": "taxamount", "type": "double"},
                        {"name": "lifecyclestatus", "type": "string"},
                        {"name": "billingstatus", "type": "string"},
                        {"name": "deliverystatus", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/salesorders/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        sales_orders.add_dependency(glue_db)

        # Athena table definition for SalesOrderItems table
        sales_order_items = glue.CfnTable(
            self,
            "SalesOrderItemsTable",
            catalog_id=self.account,
            database_name=db_name,
            table_input={
                "name": "salesorderitems",
                "tableType": "EXTERNAL_TABLE",
                "parameters": {"classification": "json", "has_encrypted_data": "false"},
                "storageDescriptor": {
                    "columns": [
                        {"name": "salesorderid", "type": "string"},
                        {"name": "salesorderitem ", "type": "string"},
                        {"name": "productid", "type": "string"},
                        {"name": "noteid ", "type": "string"},
                        {"name": "currency", "type": "string"},
                        {"name": "grossamount", "type": "double"},
                        {"name": "netamount", "type": "double"},
                        {"name": "taxamount", "type": "double"},
                        {"name": "itematpstatus", "type": "string"},
                        {"name": "opitempos", "type": "string"},
                        {"name": "quantity", "type": "double"},
                        {"name": "quantityunit", "type": "string"},
                        {"name": "deliverydate", "type": "string"},
                    ],
                    "location": f"{datalake_bucket.s3_url_for_object()}/{demo_dataset_name}/salesorderitems/",
                    "inputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        "parameters": {"skip.header.line.count": "1"},
                    },
                },
            },
        )
        sales_order_items.add_dependency(glue_db)
