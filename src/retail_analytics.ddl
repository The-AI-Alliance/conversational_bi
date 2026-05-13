CREATE TABLE IF NOT EXISTS retail.shopify (
	id string,
	published timestamp,
	verb string,
	identity_id string,
	interaction_id string,
	interaction_category string,
	ecommerce_orderDate string,
	ecommerce_orderNumber integer,
	ecommerce_identifier string,
	ecommerce_paymentUrl string,
	target_schemaOrg_cartId string,
	target_schemaOrg_checkoutId bigint,
	target_schemaOrg_orderId bigint,
	report_currency string,
	report_discounts double,
	report_grossSales double,
	report_netSales double,
	report_returns double,
	report_shipping double,
	report_totalSales double,
	report_totalTaxes double,
	ts_published string,
	ts_published_date string,
	ts_published_ym1 string,
	ts_published_yw1 string,
	ts_published_dow  string
)

CREATE TABLE IF NOT EXISTS retail.sei_models (
	code	string,	/* Internal unique identifier of the model (primary key).*/
	name	string,	/* Descriptive model name (e.g., “Cam. Of. 1º Equip. m/c 12/13”).*/
	doc_entry	integer,	/* Sequential entry ID (may link to related configuration document).*/
	user_sign	integer,	/* Internal SAP user ID responsible for creation or last change.*/
	create_date	timestamp,	/* Date when the record was created.*/
	create_time	integer,	/* Time of creation (integer timestamp or HHMM).*/
	update_date	timestamp,	/* Date when the record was last modified.*/
	update_time	integer,	/* Time of last update.*/
	data_source	string,	/* Source of the record (I = imported, O = operational).*/
	u_seitalla	string,	/* Specific size (e.g., “Adulto”, “6-XXL”).*/
	u_seitall_n	string,	/* Size group name (e.g., “Tallaje Adulto”).*/
	u_seicolor	string,	/* Short color code or label (e.g., “12-13”).*/
	u_seicolo_n	string,	/* Long color description (e.g., “UMBRO 12-13”).*/
	u_seitemp	string,	/* Season code (e.g., “T12-13”).*/
	u_seitemp_n	string,	/* Season description (e.g., “Temporada 12/13”).*/
	u_seimed_n	string,	/* Measurement or size label (e.g., “única”).*/
	u_seigrupo	integer,	/* Group code for higher-level product categorization.*/
	u_seiivap	string,	/* VAT purchase group (e.g., “S3”).*/
	u_seipur_it	string,	/* Purchase item indicator (Y/N).*/
	u_seiivas	string,	/* VAT sales group (e.g., “R3”).*/
	u_seialm	string,	/* Warehouse or storage code associated with the model.*/
	u_seifrzn	string,	/* Frozen flag (Y/N) — indicates if model is inactive.*/
	u_seicom	string,	/* Commercial group or sales category (e.g., “mercancía de Store”).*/
	u_seiimg	string,	/* Path to product image (e.g., \\Servsap\sap_data\Bitmaps\tienda\1.jpg).*/
	u_seifam	string,	/* Family code (numeric or short identifier).*/
	u_seifam_n	string,	/* Family description (e.g., “TEXTIL”).*/
	u_seisub_fa	string,	/* Sub-family code (may link to product hierarchy).*/
	u_seisub_fn	string	/* Sub-family name or description.*/
)

CREATE TABLE IF NOT EXISTS retail.sales_invoices_oinv (
	doc_entry	bigint,	/* Internal SAP system ID (primary key).*/
	doc_num	bigint,	/* Visible invoice number assigned by SAP (user-facing).*/
	doc_type	string,	/* Invoice type: I = item-based, S = service-based.*/
	printed	string,	/* Indicates if the invoice was printed (Y/N).*/
	invnt_sttus	string,	/* Inventory status (O = open, C = closed).*/
	doc_date	timestamp,	/* Posting date of the invoice (used for accounting).*/
	doc_due_date	timestamp,	/* Due date for payment (from customer payment terms).*/
	vat_sum	double,	/* Total VAT amount of the document.*/
	disc_prcnt	double,	/* Global discount percentage applied to the entire document.*/
	disc_sum	double,	/* Total discount amount applied at the document level.*/
	doc_total	double,	/* Gross total of the invoice, including VAT.*/
	gros_profit	double,	/* Gross profit amount from the transaction.*/
	ref1	bigint,	/* Reference field linking to another document or external identifier.*/
	comments	string,	/* Free-text field containing comments or descriptions about the invoice.*/
	jrnl_memo	string,	/* Journal entry memo or short accounting note (e.g., “Facturas de clientes - T02”).*/
	trans_id	bigint,	/* Transaction (journal entry) ID linking to accounting module.*/
	group_num	integer,	/* Payment terms group number (-1 = immediate, 12 = net terms, etc.).*/
	doc_time	integer,	/* Time of document creation or posting (HHMM format).*/
	slp_code	bigint,	/* Salesperson code assigned to the transaction.*/
	update_date	timestamp,	/* Date of last modification.*/
	create_date	timestamp,	/* Date when the invoice record was created in SAP.*/
	series	integer,	/* Invoice numbering series used for document sequencing.*/
	tax_date	timestamp,	/* Date used for tax calculation (may differ from posting date).*/
	data_source	string,	/* Data origin flag (O = operational, I = imported, N = native).*/
	finnc_priod	integer,	/* Financial period or fiscal accounting period associated with this document.*/
	user_sign	integer,	/* SAP internal user ID that created or last modified the record.*/
	draft_key	integer,	/* Temporary reference ID for draft invoices (used before posting).*/
	station_id	integer,	/* POS or system terminal ID from which the invoice originated.*/
	round_dif	integer,	/* Rounding difference amount (e.g., small currency adjustments).*/
	rounding	string,	/* Indicates whether rounding was applied (Y/N).*/
	pey_method	string,	/* Payment method (e.g., “C-CARGO CUENTA”, “TARJETA”).*/
	max_dscn	string,	/* Maximum discount flag (Y/N).*/
	max1099	double,	/* Internal SAP field; used in some versions for reporting cumulative document values.*/
	vatfirst	string,	/* Indicates whether VAT was applied before discounts (Y/N).*/
	ctl_account	bigint,	/* Control account for the business partner (e.g., Accounts Receivable – 43000000).*/
	owner_code	integer,	/* Code of the SAP user or employee responsible for the document.*/
	bpname_ow	string,	/* Business partner name (customer) associated with the invoice.*/
	srv_gp_prcnt	integer	/* Service gross profit percentage (for service-type invoices).*/
)

CREATE TABLE IF NOT EXISTS retail.sales_credit_notes_rin1 (
	doc_entry	integer,	/* Foreign key linking to the document header (sales_credit_notes_orin.doc_entry).*/
	line_num	integer,	/* Line number within the credit note document.*/
	item_code	string,	/* Item or SKU code (foreign key to master_articles_oitm.item_code).*/
	dscription	string,	/* Description of the item or service on the credit note line.*/
	quantity	integer,	/* Quantity of items credited in this line.*/
	price	double,	/* Unit price of the item excluding VAT.*/
	disc_prcnt	double,	/* Discount percentage applied at the line level.*/
	line_total	double,	/* THIS FIELD REPRESENTS THE BILLING REFUND AMOUNT FOR AN ARTICLE.*/
	whs_code	string,	/* Warehouse code where goods are credited from.*/
	slp_code	integer,	/* Salesperson code responsible for the transaction.*/
	acct_code	bigint,	/* G/L account linked to the line (e.g., sales, discounts, or adjustments).*/
	gross_buy_pr	double,	/* Item cost price at the time of transaction.*/
	price_bef_di	double,	/* Unit price before discounts.*/
	doc_date	timestamp,	/* Posting date of the document line (matches header doc_date).*/
	ocr_code	string,	/* Primary cost center code.*/
	code_bars	string,	/* Barcode or EAN code associated with the item.*/
	vat_prcnt	integer,	/* VAT percentage applied to this line (e.g., 21).*/
	vat_group	string,	/* VAT group code applied (e.g., “R3”).*/
	price_af_vat	double,	/* Unit price including VAT.*/
	factor1	integer,	/* Multiplier factor used in quantity or pricing calculation (usually 1).*/
	vat_sum	double,	/* Total VAT amount for this line.*/
	grss_profit	double,	/* Gross profit value for this line.*/
	inmprice	double,	/* Inventory price or standard cost per item unit.*/
	owner_code	integer,	/* SAP user or employee responsible for creating the document line.*/
	stock_sum	double,	/* Stock balance or total value of stock movement at line level.*/
	gtotal	double,	/* Line total including VAT.*/
	distrib_exp	string,	/* Distribution expense indicator (Y/N) for freight or additional costs.*/
	gross_base	integer,	/* Base gross amount before deductions or taxes.*/
	cogs_ocr_cod	string,	/* Cost center associated with the cost of goods sold (COGS).*/
	ocr_code2	string,	/* Secondary cost center or dimension 2 code.*/
	stock_value	double,	/* Inventory value associated with the credited quantity.*/
	vat_grp_src	string,	/* VAT group source type (M = manual, A = automatic).*/
	gpbef_disc	double,	/* Gross profit before discount (absolute value).*/
	u_seimot_desc	string,	/* Custom field — sales motion or promotion descriptor (e.g., campaign code).*/
	u_seitentry	bigint,	/* Custom field — related entry ID in transaction linkage (foreign document).*/
	u_seitline	integer,	/* Custom field — related line number in linked document.*/
	u_seidesc	double	/* Custom field — adjustment or special discount percentage.*/
)

CREATE TABLE IF NOT EXISTS retail.sales_credit_notes_orin (
	doc_entry	integer,	/* Internal system ID (primary key) of the credit note document.*/
	doc_num	bigint,	/* Visible document number assigned by SAP to the credit note.*/
	doc_type	string,	/* Document type (S = service, I = item-based).*/
	printed	string,	/* Indicates whether the document was printed (Y/N).*/
	invnt_sttus	string,	/* Inventory status of the document (O = open, C = closed).*/
	doc_date	timestamp,	/* Accounting date (posting date) of the credit note.*/
	vat_sum	double,	/* Total VAT amount for the credit note.*/
	disc_prcnt	double,	/* Overall document-level discount percentage applied to the credit note.*/
	disc_sum	double,	/* Total discount amount applied to the document (in local currency).*/
	doc_total	double,	/* Total gross amount of the credit note (including VAT).*/
	gros_profit	double,	/* Total gross profit from the transaction (before taxes).*/
	ref1	bigint,	/* Reference number (often linked to original invoice or document chain).*/
	comments	string,	/* Free-text field used for comments, notes, or explanations attached to the credit note.*/
	jrnl_memo	string,	/* Journal memo or reference text used in accounting entries.*/
	trans_id	bigint,	/* Journal entry ID linking the credit note to accounting transactions.*/
	doc_time	integer,	/* Time when the document was created or posted (numeric, HHMM format).*/
	slp_code	integer,	/* Salesperson code responsible for the transaction (non-personal numeric ID).*/
	update_date	timestamp,	/* Date when the record was last updated.*/
	create_date	timestamp,	/* Date when the document was created in the SAP system.*/
	series	integer,	/* Series number used to generate the document number (used for numbering control).*/
	tax_date	timestamp,	/* Tax calculation date (often identical to doc_date in accounting).*/
	data_source	string,	/* Origin of the record (I = imported, O = operational, N = native SAP).*/
	finnc_priod	integer,	/* Financial period or fiscal month in which the document was recorded.*/
	user_sign	integer,	/* Internal user ID of the SAP user who created or last modified the document.*/
	station_id	integer,	/* POS or workstation identifier where the document was created.*/
	pey_method	string,	/* Payment method assigned to the credit note (e.g., “C-CARGO CUENTA”).*/
	ctl_account	bigint,	/* Control account used for the business partner involved (e.g., accounts receivable).*/
	owner_code	integer,	/* Internal code of the employee or user responsible for the transaction.*/
	pay_to_code	string,	/* Default “Bill To” address or customer payment destination. (May contain business partner location references.)*/
	last_pmn_typ	string,	/* Type of last payment method used (R = receipt, T = transfer, etc.).*/
	srv_gp_prcnt	integer,	/* Service gross profit percentage (used when credit notes involve services).*/
	create_ts	integer,	/* Timestamp (in seconds or milliseconds) representing document creation time.*/
	update_ts	integer,	/* Timestamp of last update operation.*/
	u_seicp	string,	/* Custom field — internal classification or control code for customer processing.*/
	u_seinom	string,	/* Custom field — NAME of the STORE THAT SOLD THAT ARTICLE (e.g., “Tienda Estadio”).*/
	u_seidesc	double,	/* Custom field — auxiliary discount or description value.*/
	u_seiinf_dev	string,	/* Custom field — device or store identifier (e.g., “02” = terminal code).*/
	u_seiimp_pd	double,	/* Custom field — indicates if import payment or customs duties were applied.*/
	u_seitienda	string,	/* Custom field — store identifier linked to retail systems integration.*/
	u_seitipo	integer,	/* Custom field — transaction type indicator (e.g., sale, return, adjustment).*/
	u_seitpv	string	/* Custom field — flag indicating POS-originated transaction (Y/N).*/
)

CREATE TABLE IF NOT EXISTS retail.rel_articles_price_lists_itm (
	item_code	string,	/* Unique item identifier (SKU) in SAP; corresponds to OITM.item_code.*/
	price_list	integer,	/* Identifier of the price list (list_num) to which this record belongs.*/
	price	double,	/* Unit price for the item in this specific price list.*/
	currency	string,	/* Currency code of the price (e.g., EUR, USD).*/
	ovrwritten	string,	/* Indicates whether the price has been manually overwritten (Y/N).*/
	factor	double,	/* Multiplication factor applied over the base price list to calculate this item’s price.*/
	base_plnum	integer	/* Base price list number used as reference for price derivation.*/
)

CREATE TABLE IF NOT EXISTS retail.master_warehouses_owhs (
	whs_code	string,	/* Warehouse code (unique identifier used in SAP, e.g., “02”, “TT”).*/
	whs_name	string,	/* Descriptive warehouse name (e.g., “Estadio”, “Tienda Nervión”).*/
	data_source	string,	/* Data origin flag (I = imported, O = operational, N = native SAP).*/
	user_sign	integer,	/* Internal user ID of the SAP user who created or last updated the record.*/
	street	string,
	city	string,	/* City name associated with the warehouse’s physical location. (May contain personal/geographic data → redact or anonymize if needed.)*/
	county	string,	/* County or province name of the warehouse. (Also geographic data.)*/
	state	integer,	/* Regional or administrative code of the warehouse’s location (often numeric).*/
	create_date	timestamp,	/* Date when the warehouse master record was created in SAP.*/
	update_date	timestamp,	/* Date when the warehouse master data was last modified.*/
	street_no string,
	pur_bal_act	bigint,	/* G/L account used for purchase balance postings related to this warehouse.*/
	bin_activat	string,	/* Indicates whether bin locations (sub-storage bins) are activated for this warehouse (Y/N).*/
	inactive	string,	/* Indicates whether the warehouse is inactive and no longer used for transactions.*/
	u_seifac_v	string,	/* Custom field – indicates whether the warehouse is authorized for sales invoicing (Y/N).*/
	u_seiofe_v	string,	/* Custom field – marks whether the warehouse can process sales offers (Y/N).*/
	u_seiped_c	string,	/* Custom field – indicates whether the warehouse can handle purchase orders (Y/N).*/
	u_seient_m	string,	/* Custom field – marks whether the warehouse is enabled for merchandise entry (Y/N).*/
	u_seistk	integer,	/* Custom field – internal flag for stock control or synchronization indicator.*/
	u_seitipo	integer,	/* Custom field – warehouse type (e.g., 1 = Physical, 2 = POS, etc.).*/
	u_seice_be	string /* Custom field – internal business entity or cost center code related to the warehouse (e.g., “COM0201”).*/
)

CREATE TABLE IF NOT EXISTS retail.master_stock_oitw (
	item_code	string,	/* Unique SAP item identifier (SKU) associated with this warehouse record.*/
	whs_code	string,	/* Warehouse code identifying the physical or logical warehouse location.*/
	on_hand	double,	/* Physical quantity of the item available on hand in this warehouse.*/
	is_commited	double,	/* Quantity currently committed to open documents (sales, deliveries, etc.).*/
	user_sign	double,	/* Internal user ID who created or last updated the record.*/
	locked	string,	/* Flag indicating if the warehouse item is locked for transactions (Y/N).*/
	bal_invnt_ac	string,	/* G/L account used for inventory balance postings in this warehouse.*/
	sale_cost_ac	string,	/* G/L account used for sales cost (COGS) postings.*/
	transfer_ac	string,	/* G/L account used to record stock transfer transactions.*/
	revenues_ac	string,	/* G/L account used to post sales revenues for this item and warehouse.*/
	variance_ac	string,	/* G/L account used to post inventory variances or adjustments.*/
	expenses_ac	string,	/* General expense account linked to item cost transactions.*/
	eurevenu_ac	string,	/* Revenue account used for EU transactions (sales).*/
	euexpens_ac	string,	/* Expense account used for EU transactions (cost of goods sold).*/
	fr_revenu_ac	string,	/* Revenue account for foreign transactions (outside EU).*/
	fr_expens_ac	string,	/* Expense account for foreign transactions (outside EU).*/
	exchange_ac	string,	/* G/L account used for exchange rate differences related to stock.*/
	balance_acc	string,	/* G/L account used for balance adjustments between valuation layers.*/
	pareturn_ac	string,	/* Account used for purchase return transactions.*/
	wip_acct	string,	/* G/L account used for Work In Progress (WIP) inventory transactions.*/
	create_date	timestamp,	/* Date when this item–warehouse record was created in the system.*/
	update_date	timestamp,	/* Last date when this warehouse record was updated.*/
	neg_stck_act	string,	/* G/L account used when the item allows negative stock balances.*/
	stk_in_tn_act	string	/* Stock account used for stock-in-transit movements between warehouses.*/
)

CREATE TABLE IF NOT EXISTS retail.master_price_lists_opln (
	list_num	integer,	/* Unique identifier for the price list (foreign key linked to price_list in ITM1).*/
	list_name	string,	/* Descriptive name of the price list (e.g., “Lista de precios de compra”).*/
	data_source	string,	/* Indicates data origin (N = native SAP, I = imported, O = operational).*/
	user_sign	integer,	/* SAP internal user ID that created or modified the record.*/
	is_gross_prc	string,	/* Flag specifying whether prices in this list include VAT (Y/N).*/
	update_date	timestamp,	/* Timestamp of the latest update to the price list.*/
	u_seidto_abo	string,	/* Custom field — identifies if list applies to direct-to-abonado (subscriber) pricing.*/
	u_seiimp_inc	string	/* Custom field — marks whether import duties or indirect costs are included in prices.*/
)

CREATE TABLE IF NOT EXISTS retail.master_inventory_log_oinm (
	trans_num	bigint,	/* Unique transaction number for the inventory movement (primary key).*/
	trans_type	double,	/* Type of transaction (e.g., 60 = goods issue, 59 = goods receipt, etc.).*/
	created_by	double,	/* Internal user ID of the system user who created the record.*/
	base_ref	string,	/* Reference number of the originating document (e.g., goods receipt, invoice, or adjustment).*/
	doc_line_num	bigint,	/* Line number within the associated document.*/
	doc_date	timestamp,	/* Document posting date in the inventory log.*/
	doc_due_date	timestamp,	/* Due date related to the document (often same as doc_date).*/
	ref1	string,	/* First reference field — typically stores document or transaction identifiers.*/
	ref2	string,	/* Second reference field — often holds additional transaction notes.*/
	comments	string,	/* Additional remarks or free-text comments for the transaction.*/
	jrnl_memo	string,	/* Journal memo or note appearing in the accounting entry.*/
	doc_time	double,	/* Time of document creation or posting (numeric, HHMM format).*/
	item_code	string,	/* Unique SAP item code (SKU) identifying the material or product.*/
	dscription	string,	/* Description of the item or movement (usually item name).*/
	in_qty	double,	/* Quantity of stock moved into inventory (receipts, adjustments, returns).*/
	out_qty	double,	/* Quantity of stock moved out of inventory (issues, deliveries, adjustments).*/
	price	double,	/* Unit price for the transaction, excluding VAT.*/
	warehouse	string,	/* Warehouse code where the movement occurred.*/
	tree_type	string,	/* Type of bill-of-material (BOM) tree (N = none, S = sales, P = production).*/
	slp_code	double,	/* Salesperson or responsible code (numeric, non-personal identifier).*/
	tax_date	timestamp,	/* Date used for tax accounting purposes.*/
	data_source	string,	/* Source of data entry (O = operational, I = imported, etc.).*/
	user_sign	double,	/* Internal user ID who last modified the record.*/
	calc_price	double,	/* Calculated inventory price used for valuation (unit cost basis).*/
	trnsfr_act	string,	/* Account used for transfer postings between warehouses.*/
	return_act	string,	/* Account used for return transactions.*/
	cost_act	string,	/* G/L account used for cost postings associated with the transaction.*/
	balance	double,	/* Current balance of stock or quantity after the transaction.*/
	create_date	timestamp,	/* Date on which the record was created in the system.*/
	base_line	double,	/* Line number of the source document linked to this transaction.*/
	trans_value	double,	/* Total monetary value of the transaction (positive or negative).*/
	invnt_act	string,	/* Inventory account linked to the transaction.*/
	open_value	double,	/* Open inventory value not yet cleared by accounting entries.*/
	allocation	double,	/* Allocated quantity or value reserved for the transaction (typically 0 if not allocated).*/
	open_alloc	double,	/* Open allocation value pending assignment.*/
	cogs_val	double,	/* Cost of goods sold (COGS) value derived from this movement.*/
	ioff_inc_acc	string,	/* G/L account for offsetting increase transactions.*/
	ioff_inc_val	double,	/* Value posted to the offsetting increase account.*/
	doff_dec_acc	string,	/* G/L account for offsetting decrease transactions.*/
	doff_dec_val	double,	/* Value posted to the offsetting decrease account.*/
	ocr_code	string,	/* Primary cost center code linked to this inventory transaction.*/
	ocr_code2	string,	/* Secondary cost center or project code for multi-dimensional reporting.*/
	is_first_order	boolean	/* Boolean flag indicating whether this record belongs to the first stock order (TRUE/FALSE).*/
)

CREATE TABLE IF NOT EXISTS retail.master_articles_oitm (
	item_code	string,	/* Unique product identifier (SKU) in SAP.*/
	item_name	string,	/* THIS FIELD REPRESENTS THE NAME OF AN ARTICLE.*/
	itms_grp_cod	double,	/* Internal code of the item group or category.*/
	vat_gourp_sa	string,	/* VAT group used for sales transactions.*/
	code_bars	string,	/* Item barcode (EAN-13 or internal format) used for scanning.*/
	prchse_item	string,	/* Indicates if the item can be purchased (Y/N).*/
	sell_item	string,	/* Indicates if the item can be sold (Y/N).*/
	invnt_item	string,	/* Flag indicating whether the item is an inventoried item (Y/N).*/
	on_hand	double,	/* Quantity of this item currently available in stock.*/
	is_commited	double,	/* Quantity or flag showing whether stock is currently committed to open orders.*/
	lst_evl_pric	double,	/* Last evaluated cost of the item.*/
	lst_evl_date	timestamp,	/* Last valuation date when the item’s cost was recalculated.*/
	eval_system	string,	/* Valuation system used for cost calculation (A = Average, S = Standard).*/
	user_sign	double,	/* System user ID who created or modified the record.*/
	pictur_name	string,	/* File name or path of the associated item image.*/
	last_pur_prc	double,	/* Price of the most recent purchase.*/
	last_pur_dat	timestamp,	/* Date of the most recent purchase transaction for this item.*/
	create_date	timestamp,	/* Creation date of the item in the system.*/
	update_date	timestamp,	/* Last update date of the item record.*/
	vat_group_pu	string,	/* VAT group used for purchase transactions.*/
	avg_price	double,	/* Average cost price of the item, used for valuation and reporting.*/
	data_source	string,	/* Origin system of the record (O = Operational, I = Imported, etc.).*/
	valid_for	string,	/* Indicates if the item is currently valid/active (Y/N).*/
	frozen_for	string,	/* Indicates whether the item is frozen for transactions (Y/N).*/
	frozen_from	timestamp,	/* Date from which the item was frozen (inactive for operations).*/
	doc_entry	bigint,	/* Internal SAP entry ID linked to the item record.*/
	glmethod	string,	/* Inventory valuation method used for posting to the general ledger (C = Continuous, P = Periodic).*/
	by_wh	string,	/* Flag indicating whether the item is managed by warehouse (Y/N).*/
	stock_value	double,	/* Total current stock value for the item.*/
	planing_sys	string,	/* Planning system type (M = Manual, O = Order-driven, etc.).*/
	series	double,	/* Series number associated with the item or campaign.*/
	`number`	double,	/* Sequential numeric identifier or item reference counter.*/
	no_discount	string,	/* Indicates if the item is excluded from discounts (Y/N).*/
	u_seimodel	string,	/* Custom field: model identifier.*/
	u_seicarta	string,	/* Custom field: catalog or season identifier (e.g. 12-13).*/
	u_seitaje	string,	/* Custom field: target age group (e.g. Adulto, Infantil).*/
	u_seicolor	string,	/* Custom field: color code (e.g. 100).*/
	u_seicolo_n	string,	/* Custom field: color name (e.g. Rojo).*/
	u_seitalla	string,	/* Custom field: size or sizing category (e.g. S, M, L, 6-XXL).*/
	u_seitemp	string,	/* Custom field: season code (e.g. T12-13).*/
	u_seifam	string,	/* Custom field: product family or division code.*/
	u_seicompo	string,	/* Custom field: item composition or material description.*/
	`ref`	string,	/* Internal reference or supplier code.*/
	cmp_name	string,	/* Defined by Retail Team - Campaign or commercial collection name (e.g. LANZAMIENTO CASTORE 24/25).*/
	cmp_target_size	string,	/* Target audience or segment size (e.g. 1.MAN, 1.WOMAN).*/
	cmp_kit_type	string,	/* Defined by Retail Team - Kit or package type within the campaign (e.g. 1.HOME, 2.AWAY).*/
	cmp_full_name	string,	/* Defined by Retail Team - Full descriptive name of the campaign or collection the item belongs to.*/
	cmp_short_name	string	/* Abbreviated or compact version of the campaign name.*/
)

CREATE TABLE IF NOT EXISTS retail.items_shopify (
	id string,
	orderQuantity integer,
	orderedItem_name string,
	orderedItem_alternateName string,
	orderedItem_model string,
	orderedItem_grossPrice_maxPrice double,
	orderedItem_grossPrice_price double,
	orderedItem_totalDiscount_price double,
	orderedItem_totalPayment_price double
)

CREATE TABLE IF NOT EXISTS retail.inventory_stock_inv1 (
	doc_entry	bigint,	/* Unique SAP document entry identifier.*/
	line_num	bigint,	/* Sequential line number in the document.*/
	base_ref	string,	/* External or internal reference identifier of the base document.*/
	base_type	bigint,	/* Type of base document (e.g., -1 = manual entry, 13 = sales order, etc.).*/
	base_entry	double,	/* Internal SAP entry number of the base document.*/
	base_line	double,	/* Line number within the base document linked to this transaction.*/
	item_code	string,	/* Unique item identifier (SKU) in SAP.*/
	dscription	string,	/* Description of the inventory line or item.*/
	quantity	double,	/* Quantity of goods moved in this transaction.*/
	ship_date	timestamp,	/* Planned or actual shipping date of the transaction.*/
	price	double,	/* Net unit price of the item (excluding VAT).*/
	disc_prcnt	double,	/* Discount percentage applied to the transaction line.*/
	line_total	double,	/* THIS VALUE REPRESENTS THE BILLING AMOUNT FOR AN ARTICLE. */
	whs_code	string,	/* Warehouse code where the stock movement occurred.*/
	slp_code	bigint,	/* Salesperson or responsible agent code (numeric, not personal).*/
	acct_code	string,	/* General Ledger account associated with the stock transaction (used for financial posting).*/
	gross_buy_pr	double,	/* Gross purchase price of the item.*/
	price_bef_di	double,	/* Unit price before discount application.*/
	doc_date	timestamp,	/* Document date of the inventory posting (transaction date).*/
	ocr_code	string,	/* Primary cost center or operational code assigned to the transaction.*/
	code_bars	string,	/* Product barcode (EAN or internal). Used for product identification.*/
	vat_prcnt	double,	/* VAT percentage rate applied.*/
	vat_group	string,	/* VAT group code applied to the line.*/
	price_af_vat	double,	/* Unit price including VAT.*/
	factor1	double,	/* Conversion factor between units of measure (usually 1).*/
	base_doc_num	double,	/* Reference document number from which this transaction originates (e.g. order, invoice).*/
	vat_sum	double,	/* Total VAT amount for the line.*/
	finnc_priod	bigint,	/* Financial period identifier (links to accounting calendar).*/
	grss_profit	double,	/* Gross profit associated with the line (sales − cost).*/
	inmprice	double,	/* Inventory price used for valuation (usually unit cost).*/
	orig_item	string,	/* Original item code before substitutions or transformations.*/
	base_qty	double,	/* Quantity from the base document used in the current transaction.*/
	base_opn_qty	double,	/* Open quantity remaining on the base document at transaction time.*/
	owner_code	double,	/* Internal owner or responsible user code (non-personal numeric ID).*/
	stock_sum	double,	/* Current stock sum or total quantity after the transaction.*/
	base_price	string,	/* Base price indicator or currency code associated with the original document.*/
	gtotal	double,	/* Grand total amount of the line, including VAT and discounts.*/
	distrib_exp	string,	/* Distribution expense flag or type (Y/N).*/
	desc_ow	string,	/* Internal flag or description of the origin warehouse.*/
	gross_base	double,	/* Gross base value of the transaction before adjustments.*/
	qty_to_ship	double,	/* Remaining quantity to ship or deliver.*/
	ordered_qty	double,	/* Quantity originally ordered for this transaction.*/
	cogs_ocr_cod	string,	/* Cost center or operational area responsible for COGS posting.*/
	cogs_acct	string,	/* Cost-of-Goods-Sold (COGS) account used in posting.*/
	act_del_date	timestamp,	/* Actual delivery date of the stock movement.*/
	ocr_code2	string,	/* Secondary cost center or project code (used for multidimensional analysis).*/
	stock_value	double,	/* Total stock value after the transaction.*/
	vat_grp_src	string,	/* VAT group source indicator (sales or purchase).*/
	gpbef_disc	double,	/* Gross price before discount (unit basis).*/
	u_seimot_desc	string,	/* Custom field — description of stock movement motive.*/
	u_seidesc	double	/* Custom field — internal descriptor or adjustment factor.*/
)

CREATE TABLE IF NOT EXISTS retail.calendar (
	`_ts_date`				timestamp,	/* Transactional date in calendar (YYYY-MM-DD).*/
	`_ts_year`				integer,		/* Year extracted from _ts_date.*/
	`_ts_quarter`			string,		/* Quarter label (Q1–Q4).*/
	`_ts_ym1`				date,		/* Year-month key for grouping (e.g. 2012-09-01).*/
	`_ts_yw1`				string,		/* Year-week key (e.g. 2012-09-24).*/
	`_ts_month_name`		string,		/* Month name (e.g. September).*/
	`_ts_season`			string,		/* Season code (e.g. 12.13).*/
	`_ts_season_month`		string,		/* Combined season-month key (e.g. 12.13-09-Sep).*/
	fiscal_semester			string,		/* Fiscal semester (e.g. Sem.1).*/
	fiscal_quarter			string,		/* Fiscal quarter (e.g. Q1).*/
	fiscal_month_name		string,		/* Fiscal month name.*/
	`_hier_fiscal_semester`	string,		/* Hierarchical fiscal semester label (e.g. 12.13-Sem.1).*/
	`_hier_fiscal_quarter`	string,		/* Hierarchical fiscal quarter label (e.g. 12.13-Q1).*/
	`_hier_fiscal_month`	string		/* Hierarchical fiscal month label (e.g. 12.13-03-Sep). Used for fiscal reporting.*/
)