/* Electronics retail analytics — DuckDB schema (generated from live parquet files).
   Schema prefix: retail2 (compatibility) and retail (DDL convention) — both 
   point to the same parquet files via views registered in execute.py. */

/* Product master.  One row per SKU. */
CREATE TABLE retail.master_articles_oitm (
	item_code	string,	/* Unique item identifier (SKU). Primary key. */
	item_name	string,	/* Human-readable item name (used for IN-clause filters from Step 3.5). */
	sell_item	string,	/* 'Y' if the item can be sold, 'N' otherwise. */
	valid_for	string,	/* 'Y' if the item is currently valid, 'N' otherwise. */
	create_date	timestamp	/* Date when the item was added to the catalogue. */
);

/* Sales invoice LINES.  One row per item per sales document. */
CREATE TABLE retail.inventory_stock_inv1 (
	doc_date	timestamp,	/* Posting date of the sales invoice line. */
	item_code	string,	/* FK to master_articles_oitm.item_code. */
	ocr_code	string,	/* Cost-center / store code. Always filter IN ('STR01','STR02','STR03','STR04'). */
	line_total	double,	/* Line-level billing amount (sales revenue contribution). */
	quantity	double	/* Units sold on this line. */
);

/* Credit-note LINES.  One row per item per credit-note document. */
CREATE TABLE retail.sales_credit_notes_rin1 (
	doc_date	timestamp,	/* Posting date of the credit note line. */
	item_code	string,	/* FK to master_articles_oitm.item_code. */
	ocr_code	string,	/* Cost-center / store code. Always filter IN ('STR01','STR02','STR03','STR04'). */
	line_total	double,	/* Line-level refund amount (subtract from inv1.line_total for net billing). */
	quantity	double	/* Units returned on this line. */
);

/* Stock level per item per warehouse. */
CREATE TABLE retail.master_stock_oitw (
	item_code	string,	/* FK to master_articles_oitm.item_code. */
	whs_code	string,	/* FK to master_warehouses_owhs.whs_code. */
	on_hand	double	/* Current units of this item in this warehouse. */
);

/* Warehouse master.  One row per warehouse. */
CREATE TABLE retail.master_warehouses_owhs (
	whs_code	string,	/* Unique warehouse identifier. Primary key. */
	whs_name	string,	/* Human-readable warehouse name. */
	inactive	string	/* 'Y' if the warehouse is inactive, 'N' otherwise. */
);

/* Inventory movement log.  Receipts, shipments, transfers. */
CREATE TABLE retail.master_inventory_log_oinm (
	item_code	string,	/* FK to master_articles_oitm.item_code. */
	doc_date	timestamp,	/* Date of the inventory movement. */
	in_qty	double,	/* Units received (positive movement). */
	out_qty	double,	/* Units shipped/consumed (negative movement). */
	trans_type	integer,	/* Transaction type code (e.g., sale, transfer, adjustment). */
	warehouse	string,	/* Warehouse where the movement occurred. */
	card_code	string	/* Business-partner code (customer/supplier) for the movement. */
);

/* Cost-center / store lookup. */
CREATE TABLE retail.cecos (
	ocr_code	string,	/* Cost-center / store code (matches inv1/rin1.ocr_code). */
	store_name	string	/* Human-readable store name. */
);

