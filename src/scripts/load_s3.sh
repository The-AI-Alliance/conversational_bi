#!/bin/bash
export APP_CI = <replace with app_ci variable from ./iac/aws/iac/app.py>

aws s3 cp Addresses.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/addresses/addresses.csv
aws s3 cp BusinessPartners.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/businesspartners/businesspartners.csv
aws s3 cp Employees.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/employees/employees.csv
aws s3 cp ProductCategories.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/productcategories/productcategories.csv
aws s3 cp ProductCategoryText.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/productcategorytext/productcategorytext.csv
aws s3 cp Products.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/products/products.csv
aws s3 cp ProductTexts.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/producttexts/producttexts.csv
aws s3 cp SalesOrders.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/salesorders/salesorders.csv
aws s3 cp SalesOrderItems.csv s3://$APP_CI-datalake-dev-us-east-2/bike_sales/salesorderitems/salesorderitems.csv
aws s3 cp ../ddl/retail_schema.ddl s3://$APP_CI-datalake-dev-us-east-2/schemas/retail_schema.ddl
