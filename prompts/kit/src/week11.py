import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "SQL Server 2022 setup, databases, schemas and data types",
"Get SQL Server 2022 Developer running in Docker, connect to it, create your first database and table, and choose the right data type for every column.",
[("RDBMS","Relational Database Management System: stores data in tables (rows and columns) related by keys, and enforces rules about that data."),
("SQL Server","Microsoft's RDBMS. The free <b>Developer edition</b> has every feature of Enterprise but is licensed for non-production use only."),
("T-SQL","Transact-SQL: Microsoft's dialect of SQL. Standard SQL plus extensions like <code>TOP</code>, <code>IDENTITY</code>, variables and procedures."),
("Instance","One running SQL Server service. It listens on a port (default <b>1433</b>) and hosts many databases."),
("Database","A named container of schemas, tables, views and procedures with its own files. You'll have one per application."),
("System databases","<code>master</code> (instance config), <code>model</code> (template for new DBs), <code>msdb</code> (jobs/history), <code>tempdb</code> (scratch space, rebuilt on every restart)."),
("Data file / log file","Each database has at least one <code>.mdf</code> data file (the tables) and one <code>.ldf</code> transaction log file (every change, for recovery)."),
("Filegroup","A named group of data files. Tables are created <i>on</i> a filegroup (default <code>PRIMARY</code>); big systems use extra filegroups to spread I/O. Awareness is enough for now."),
("Schema","A namespace inside a database that groups objects: <code>hr.employees</code>, <code>sales.orders</code>. The default schema is <code>dbo</code>."),
("Table","A set of rows sharing the same typed columns. Rows have no inherent order."),
("Data type","The kind of value a column stores — <code>INT</code>, <code>DECIMAL(18,2)</code>, <code>NVARCHAR(100)</code>, <code>DATE</code>… It controls storage, validation and comparison."),
("NULL","The absence of a value — not zero, not an empty string. A column declared <code>NOT NULL</code> rejects it."),
("IDENTITY","A column property that auto-generates sequential numbers per table: <code>IDENTITY(100,1)</code> starts at 100, steps by 1."),
("Sequence","A standalone number generator (<code>CREATE SEQUENCE</code>) usable across tables, with control over cache, cycle and restart."),
("Collation","The rules for sorting and comparing text. SQL Server's defaults are usually case-<b>insensitive</b> (<code>_CI_</code>), so <code>'ASHA' = 'asha'</code> is true.")],
["Developer edition is free and full-featured — perfect for this whole phase. Never use it in production.",
"The SA password must be 8+ characters with three of: uppercase, lowercase, digits, symbols — or the container silently dies.",
"Use <code>NVARCHAR</code> for anything a human types (names in any script); <code>VARCHAR</code> is fine for codes, emails, GSTINs.",
"Money is always <code>DECIMAL(18,2)</code> (or similar precision) — never <code>FLOAT</code>/<code>REAL</code>, which are approximate.",
"Prefer <code>DATE</code> and <code>DATETIME2</code> over the legacy <code>DATETIME</code> (3.33 ms rounding, min year 1753).",
"Always write two-part names: <code>hr.employees</code>, not <code>employees</code>."],
f'''
<h3>1. Run SQL Server 2022 Developer in Docker</h3>
<p>One command gives you a full SQL Server on Linux, macOS or Windows — no installer, easy to throw away and recreate:</p>
{C(r"""
docker run -d \
  --name sql2022 \
  -e "ACCEPT_EULA=Y" \
  -e "MSSQL_SA_PASSWORD=Dev@Pass123" \
  -e "MSSQL_PID=Developer" \
  -p 1433:1433 \
  -v sql2022data:/var/opt/mssql \
  mcr.microsoft.com/mssql/server:2022-latest

docker ps                        # STATUS should say "Up ..."
docker logs sql2022 | tail -5    # look for: Recovery is complete
""", "run-sqlserver.sh", lang="bash")}
{table(["Flag","Why it's there"],[
["<code>-e ACCEPT_EULA=Y</code>","Accepts the licence; the container refuses to start without it"],
["<code>-e MSSQL_SA_PASSWORD=…</code>","Password for <code>sa</code>, the built-in admin login"],
["<code>-e MSSQL_PID=Developer</code>","Edition (Developer is also the default for this image)"],
["<code>-p 1433:1433</code>","Publishes SQL Server's port so tools on your machine can connect to <code>localhost,1433</code>"],
["<code>-v sql2022data:/var/opt/mssql</code>","Named volume: your databases survive <code>docker rm sql2022</code>"],
["<code>2022-latest</code>","Latest cumulative update of SQL Server 2022"]])}
{warn("SA password rules: at least 8 characters, containing characters from three of the four sets — uppercase, lowercase, digits, symbols. If the password is too weak, the container exits within seconds with no obvious error. Always check <code>docker logs sql2022</code> when <code>docker ps</code> shows nothing.", "Gotcha")}
<p><b>On Windows without Docker:</b> download “SQL Server 2022 Developer” from Microsoft's site, choose Basic install, then install SSMS separately. Everything in these notes works identically; your server name is <code>localhost</code> (default instance) or <code>localhost\\SQLEXPRESS</code> if you picked Express.</p>
{C(r"""
docker stop sql2022      # shut down cleanly
docker start sql2022     # bring it back, data intact (thanks to the volume)
""", lang="bash")}

<h3>2. Connecting: sqlcmd, VS Code, SSMS</h3>
<p><b>sqlcmd</b> ships inside the container — the quickest smoke test:</p>
{C(r"""
docker exec -it sql2022 /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'Dev@Pass123' -C

1> SELECT @@VERSION;
2> GO
""", lang="bash")}
{C(r"""
Microsoft SQL Server 2022 (RTM-CU14) ... Developer Edition (64-bit) on Linux
""", lang="text")}
<p>The <code>-C</code> flag trusts the container's self-signed certificate — the version-18 tools encrypt connections by default and fail without it. Statements only run when you type <code>GO</code> (a batch separator understood by the tools, not by the server itself).</p>
{table(["Tool","Install","Best for"],[
["<b>VS Code MSSQL extension</b>","Install “SQL Server (mssql)” from the marketplace, add a connection: server <code>localhost,1433</code>, SQL login <code>sa</code>, “Trust server certificate” = true","Day-to-day work alongside your C# code; <kbd>Ctrl+Shift+E</kbd> runs the selection"],
["<b>SSMS</b> (Windows only)","Free download, SQL Server Management Studio","The full admin GUI: designers, execution plans, agent jobs"],
["<b>sqlcmd</b>","Already in the container; also installable on the host","Scripts, CI, quick checks"]])}
{tip("Create a dedicated connection profile now and save the password. Every example this week assumes you're connected as <code>sa</code> to <code>localhost,1433</code>.")}

<h3>3. Create a database (and peek at its files)</h3>
{C(r"""
CREATE DATABASE CompanyDb;
GO
USE CompanyDb;      -- switch this session's context to the new database
GO
SELECT name, type_desc, physical_name, size * 8 / 1024 AS size_mb
FROM sys.database_files;
""", "01_create_db.sql", lang="sql")}
{C(r"""
name          type_desc  physical_name                          size_mb
------------- ---------- -------------------------------------- -------
CompanyDb     ROWS       /var/opt/mssql/data/CompanyDb.mdf      8
CompanyDb_log LOG        /var/opt/mssql/data/CompanyDb_log.ldf  8
-- (example output; sizes come from the model database's defaults)
""", lang="text")}
<p>Every database gets a data file (<code>ROWS</code>) and a transaction log (<code>LOG</code>). Data files belong to <b>filegroups</b>; everything lands in <code>PRIMARY</code> unless you say otherwise. Large systems add filegroups to place hot tables on fast disks or to restore pieces separately — for now, just recognise the words.</p>
{C(r"""
-- Awareness only: a second filegroup with its own file
ALTER DATABASE CompanyDb ADD FILEGROUP Archive;
ALTER DATABASE CompanyDb ADD FILE
    (NAME = CompanyDb_archive, FILENAME = '/var/opt/mssql/data/CompanyDb_archive.ndf')
    TO FILEGROUP Archive;
-- CREATE TABLE dbo.old_orders (...) ON Archive;   -- table placed on it
""", lang="sql")}

<h3>4. Schemas: dbo and your own</h3>
<p>Schemas group related tables and let you secure them as a unit. If you don't specify one, you get <code>dbo</code> (“database owner”).</p>
{C(r"""
CREATE SCHEMA hr AUTHORIZATION dbo;      -- must be the only statement in its batch
GO
CREATE SCHEMA sales AUTHORIZATION dbo;
GO
-- Same table name can exist in two schemas without clashing:
-- hr.contacts (employees' emergency contacts) vs sales.contacts (leads)
""", "02_schemas.sql", lang="sql")}
{ul(["<code>hr.employees</code> reads as “the employees table in the hr schema” — schema first, then object.",
"Group by business area (<code>hr</code>, <code>sales</code>, <code>billing</code>), not by type (“tables”, “views”).",
"Permissions can be granted per schema: give the reporting team SELECT on <code>sales</code> only.",
"Always schema-qualify in code. Unqualified names make SQL Server check your default schema first — slower plan reuse and ambiguous code."])}

<h3>5. The data types you'll actually use</h3>
{table(["Type","Storage","Use for"],[
["<code>INT</code>","4 bytes, ±2.1 billion","IDs, counts, quantities — your default integer"],
["<code>BIGINT</code>","8 bytes","IDs that may exceed 2.1 billion (event logs, telemetry)"],
["<code>DECIMAL(18,2)</code>","9 bytes","<b>Money</b> and anything exact: 18 digits total, 2 after the point"],
["<code>DECIMAL(5,2)</code>","5 bytes","Small exact numbers: percentages like 18.00 (GST), 99.99"],
["<code>FLOAT</code>","8 bytes","Scientific/approximate values only — <b>never money</b>"],
["<code>VARCHAR(n)</code>","1 byte/char + 2","ASCII-safe text: emails, codes, GSTIN, URLs"],
["<code>NVARCHAR(n)</code>","2 bytes/char + 2","Unicode text: names, addresses, anything users type (नमस्ते fits)"],
["<code>CHAR(n)</code> / <code>NCHAR(n)</code>","Fixed n","Fixed-length codes: <code>CHAR(6)</code> PIN code, <code>CHAR(2)</code> state code"],
["<code>DATE</code>","3 bytes","Just a date: hire date, invoice date (0001-01-01 to 9999-12-31)"],
["<code>DATETIME2(p)</code>","6–8 bytes","Date + time, precision 0–7 fractional digits; use instead of <code>DATETIME</code>"],
["<code>TIME(p)</code>","3–5 bytes","Just a time of day: store opening hours"],
["<code>BIT</code>","1 bit (packed)","Flags: <code>is_active</code>, <code>is_deleted</code> (1, 0 or NULL)"],
["<code>UNIQUEIDENTIFIER</code>","16 bytes","GUIDs — globally unique, good for distributed systems, bad default for clustered keys (random order)"],
["<code>VARCHAR(MAX)</code> / <code>NVARCHAR(MAX)</code>","up to 2 GB","Long free text: notes, JSON. Don't use MAX “just in case”"]])}
{warn("SQL Server has a <code>MONEY</code> type, but prefer <code>DECIMAL</code>: MONEY is fixed at 4 decimal places and loses precision in intermediate division/multiplication. <code>DECIMAL(18,2)</code> (or <code>(19,4)</code> where paise fractions matter) is the industry habit.", "Note")}
{warn("<code>VARCHAR</code> stores Hindi, Tamil or emoji as <code>?</code> unless the column uses a UTF-8 collation (possible since SQL Server 2019, e.g. <code>Latin1_General_100_CI_AS_SC_UTF8</code>). The simple rule: human text → <code>NVARCHAR</code>.", "Gotcha")}

<h3>6. Your first real table: NULLs and IDENTITY</h3>
{C(r"""
CREATE TABLE hr.interns
(
    intern_id  INT            IDENTITY(100,1) NOT NULL,  -- 100, 101, 102, ...
    full_name  NVARCHAR(80)   NOT NULL,          -- must be supplied
    email      VARCHAR(100)   NOT NULL,
    phone      VARCHAR(15)    NULL,              -- optional (NULL is the default anyway)
    joined_on  DATE           NOT NULL,
    stipend    DECIMAL(10,2)  NOT NULL,
    is_active  BIT            NOT NULL DEFAULT 1
);
GO
INSERT INTO hr.interns (full_name, email, phone, joined_on, stipend)
VALUES (N'Aarav Kulkarni', 'aarav.k@company.in', '9820011111', '2026-06-01', 15000.00);

INSERT INTO hr.interns (full_name, email, joined_on, stipend)      -- phone omitted → NULL
VALUES (N'Zoya Sheikh', 'zoya.s@company.in', '2026-07-01', 18000.00);

SELECT intern_id, full_name, phone, stipend, is_active FROM hr.interns;
""", "03_first_table.sql", lang="sql")}
{C(r"""
intern_id  full_name       phone        stipend    is_active
---------- --------------- ------------ ---------- ---------
100        Aarav Kulkarni  9820011111   15000.00   1
101        Zoya Sheikh     NULL         18000.00   1
""", lang="text")}
<p>You never supply the IDENTITY column — SQL Server generates it. Note the <code>N'…'</code> prefix on Unicode literals going into <code>NVARCHAR</code> columns; without it the literal is VARCHAR and non-ASCII characters are lost before they reach the column.</p>
<h4>IDENTITY vs SEQUENCE</h4>
{C(r"""
CREATE SEQUENCE hr.badge_seq AS INT START WITH 5000 INCREMENT BY 1;
GO
SELECT NEXT VALUE FOR hr.badge_seq;      -- 5000
SELECT NEXT VALUE FOR hr.badge_seq;      -- 5001 (each call consumes a number)

-- Use it as a default, possibly shared by several tables:
CREATE TABLE hr.badges
(
    badge_no  INT NOT NULL DEFAULT (NEXT VALUE FOR hr.badge_seq),
    issued_to NVARCHAR(80) NOT NULL
);
""", lang="sql")}
{table(["","IDENTITY","SEQUENCE"],[
["Belongs to","One column of one table","The database (schema-level object)"],
["Get a value before insert","No (only after, via <code>SCOPE_IDENTITY()</code>)","Yes: <code>NEXT VALUE FOR</code>"],
["Share across tables","No","Yes"],
["Restart / change step","Awkward (<code>DBCC CHECKIDENT</code>)","<code>ALTER SEQUENCE ... RESTART</code>"],
["Typical use","Surrogate primary keys","Invoice/ticket numbers, multi-table numbering"]])}
{tip("Both can leave gaps: rolled-back inserts and server restarts consume numbers. Never promise an unbroken invoice series from IDENTITY alone — a gap-free legal series needs its own logic.")}
''',
["A weak SA password — the container starts and immediately exits; always check <code>docker logs</code>.",
"Forgetting <code>-C</code> with sqlcmd 18 and getting a certificate-verification error.",
"Using <code>FLOAT</code> for money or <code>DATETIME</code> for new columns out of habit.",
"<code>VARCHAR</code> for names — works in the demo, turns Devanagari into <code>????</code> in production.",
"Creating tables without a schema and ending up with an unplanned pile in <code>dbo</code>."],
("40 min", ["Get the container running, connect with VS Code or sqlcmd, and run <code>SELECT @@VERSION;</code>. Stop and start the container and confirm your database survives.",
"Create <code>CompanyDb</code> with schemas <code>hr</code> and <code>sales</code>. Create <code>sales.customers</code> with: identity PK candidate column, <code>NVARCHAR</code> name, <code>VARCHAR</code> email, <code>CHAR(6)</code> pin code, <code>DECIMAL(12,2)</code> credit limit, <code>BIT</code> active flag, <code>DATETIME2(0)</code> created-at.",
"Insert three customers — one with a Devanagari or Tamil name using <code>N'…'</code> — then try the same name into a <code>VARCHAR</code> column and compare what comes back."]),
[("What's the difference between an instance and a database?","An instance is the running SQL Server service (one port, one set of logins, one tempdb). It hosts many databases, each a self-contained set of schemas, tables and files."),
("Why NVARCHAR for names but VARCHAR for emails?","Names can contain any script, so they need Unicode (2 bytes/char). Email addresses are ASCII by common convention, so VARCHAR halves the storage. (A UTF-8 collation can blur this line, but the NVARCHAR habit is the safe default.)"),
("What does IDENTITY(100,5) do?","Auto-generates values for that column starting at 100, stepping by 5: 100, 105, 110… The values are per-table and assigned at insert time.")],
[("Basic","What is the difference between SQL and T-SQL?","SQL is the standard query language (SELECT, INSERT, UPDATE, DELETE, DDL). T-SQL is Microsoft's implementation plus extensions: variables, control flow, TRY/CATCH, TOP, OUTPUT, IDENTITY, stored procedures. Core queries are portable; the extensions are not."),
("Basic","Name the system databases and their roles.","master holds instance-level configuration, logins and the locations of other databases; model is the template every new database is copied from; msdb backs SQL Agent jobs, alerts and backup history; tempdb is shared scratch space for sorts, temp tables and versioning, rebuilt at every restart."),
("Basic","NULL vs an empty string vs zero?","NULL means 'no value / unknown' and is a state, not a value: it fails every = comparison and needs IS NULL. An empty string is a real VARCHAR value of length 0; zero is a real number. A phone column that's NULL means 'we don't have it'; '' would mean 'we have it and it's empty', which is usually nonsense — so model missing data as NULL."),
("Intermediate","Why is DECIMAL preferred over FLOAT and MONEY for currency?","FLOAT is binary floating point: 0.1 has no exact representation, so totals drift — unacceptable for accounts. MONEY is exact but fixed at 4 decimal places and loses precision in intermediate multiplication/division. DECIMAL(p,s) is exact, with precision you choose, and behaves predictably in arithmetic."),
("Intermediate","DATETIME vs DATETIME2 — why does the new type exist?","DATETIME stores to 1/300th of a second (values round to .000/.003/.007), starts at year 1753, and takes 8 bytes. DATETIME2 has up to 100 ns precision, dates from year 1, configurable precision and takes 6–8 bytes. Microsoft recommends DATETIME2 for all new work; DATETIME survives for compatibility."),
("Intermediate","When would you use a SEQUENCE instead of IDENTITY?","When several tables must share one number series, when you need the value before inserting (to use in related rows or return to the caller), when you need to restart or re-step the series, or when inserts come from code that wants to pre-allocate ranges. For a plain surrogate key, IDENTITY is simpler. Both can leave gaps.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Keys, constraints, ER diagrams and normalization",
"Make the database enforce your business rules with keys and constraints, read ER diagrams, and normalize a messy orders table to 3NF — then know when to stop.",
[("Primary key (PK)","The column(s) that uniquely identify each row. One per table; implies NOT NULL and unique; gets the clustered index by default."),
("Candidate key","Any column set that could serve as the PK (e.g. employee email AND employee id). The ones not chosen can become UNIQUE constraints."),
("Surrogate key","An artificial identifier with no business meaning, usually <code>INT IDENTITY</code>. The common choice for PKs."),
("Natural key","A real-world identifier (PAN, email, ISBN). Risky as a PK: they change, have exceptions, and are wide."),
("Composite key","A key of more than one column, e.g. <code>(order_id, product_id)</code> in an order-items table."),
("Foreign key (FK)","Column(s) in one table that must match a PK/UNIQUE value in another (or be NULL). Creates the relationship."),
("Referential integrity","The guarantee that FKs always point at existing rows — no orphan order for a deleted customer."),
("Referential action","What happens to child rows when the parent is deleted/updated: <code>NO ACTION</code> (default, error), <code>CASCADE</code>, <code>SET NULL</code>, <code>SET DEFAULT</code>."),
("UNIQUE constraint","No two rows may share this value (one NULL is allowed, unlike PK which allows none)."),
("CHECK constraint","A boolean rule every row must satisfy: <code>CHECK (salary > 0)</code>."),
("DEFAULT constraint","The value used when an INSERT doesn't supply the column."),
("ER diagram","Entity-Relationship diagram: boxes for tables, lines for FKs, with symbols showing cardinality (one-to-many etc.)."),
("Normalization","Structuring tables to remove redundancy, so each fact is stored once. Done in steps called normal forms."),
("Functional dependency","“Column B is determined by column A”: product name depends on product id, not on the order it appears in."),
("Denormalization","Deliberately re-introducing redundancy (copied or computed columns) to make reads faster — a conscious trade, not an accident.")],
["A table without a primary key is almost always a design bug.",
"Name your constraints (<code>PK_orders</code>, <code>FK_orders_customers</code>, <code>CK_orders_amount</code>) — auto-generated names make later ALTERs painful.",
"The FK column must match the referenced column's type exactly.",
"<code>ON DELETE CASCADE</code> is great for true parent-child (order → order items), dangerous elsewhere.",
"Normalize to 3NF by default; denormalize only with a measured reason.",
"Every CHECK/FK is one less bug class in your C# code — let the database be the last line of defence."],
f'''
<h3>1. PRIMARY KEY</h3>
{C(r"""
USE CompanyDb;
GO
-- Inline, named (preferred):
CREATE TABLE sales.customers
(
    customer_id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_customers PRIMARY KEY,
    full_name   NVARCHAR(80)  NOT NULL,
    email       VARCHAR(100)  NOT NULL,
    city        NVARCHAR(50)  NOT NULL,
    gstin       CHAR(15)      NULL
);

-- Composite key = table-level constraint (order_items: one row per product per order)
CREATE TABLE sales.order_items_demo
(
    order_id   INT NOT NULL,
    product_id INT NOT NULL,
    quantity   INT NOT NULL,
    CONSTRAINT PK_order_items_demo PRIMARY KEY (order_id, product_id)
);

INSERT INTO sales.customers (full_name, email, city)
VALUES (N'Asha Patel',  'asha@example.in',  N'Mumbai'),
       (N'Ravi Kumar',  'ravi@example.in',  N'Delhi');
""", "01_primary_keys.sql", lang="sql")}
<p>A PK is enforced by a unique index; by default it's the table's <b>clustered</b> index, meaning the rows are physically ordered by it. That's one reason an ever-increasing <code>INT IDENTITY</code> is a pleasant PK and a random GUID is not. Indexes get their own week later.</p>

<h3>2. FOREIGN KEY and what happens on delete</h3>
{C(r"""
CREATE TABLE sales.orders
(
    order_id    INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_orders PRIMARY KEY,
    customer_id INT NOT NULL
        CONSTRAINT FK_orders_customers REFERENCES sales.customers (customer_id),
    ordered_on  DATE          NOT NULL CONSTRAINT DF_orders_date DEFAULT CAST(SYSDATETIME() AS DATE),
    amount      DECIMAL(12,2) NOT NULL
);

INSERT INTO sales.orders (customer_id, amount) VALUES (1, 2499.00);   -- OK: customer 1 exists
INSERT INTO sales.orders (customer_id, amount) VALUES (99, 100.00);   -- ?
""", "02_foreign_keys.sql", lang="sql")}
{C(r"""
Msg 547, Level 16, State 0
The INSERT statement conflicted with the FOREIGN KEY constraint "FK_orders_customers".
The conflict occurred in database "CompanyDb", table "sales.customers", column 'customer_id'.
""", lang="text")}
<p>The same error protects the other direction: deleting a customer who has orders fails — unless you choose a different <b>referential action</b>:</p>
{table(["Action","On deleting the parent","Typical use"],[
["<code>NO ACTION</code> (default)","Error 547 if children exist","Most relationships — force explicit cleanup"],
["<code>ON DELETE CASCADE</code>","Children are deleted too","True compositions: order → order_items, post → comments"],
["<code>ON DELETE SET NULL</code>","Child FK becomes NULL (column must be nullable)","Optional links: employee.manager_id when the manager leaves"],
["<code>ON DELETE SET DEFAULT</code>","Child FK becomes its DEFAULT","Rare: reassign to a sentinel row like “Unassigned”"]])}
{C(r"""
CREATE TABLE sales.order_items
(
    order_id   INT NOT NULL
        CONSTRAINT FK_order_items_orders REFERENCES sales.orders (order_id)
        ON DELETE CASCADE,                       -- delete the order → its lines go too
    product_id INT NOT NULL,
    quantity   INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    CONSTRAINT PK_order_items PRIMARY KEY (order_id, product_id)
);
-- ON UPDATE CASCADE exists too (parent key value changes ripple down),
-- but with IDENTITY surrogate keys the parent key never changes, so it's rarely used.
""", lang="sql")}
{warn("Chained cascades delete more than you think, and SQL Server rejects designs where a table could be cascaded from two paths (error 1785, “may cause cycles or multiple cascade paths”). Keep CASCADE for one level of true ownership; elsewhere delete children explicitly.", "Careful")}

<h3>3. UNIQUE, CHECK and DEFAULT</h3>
{C(r"""
ALTER TABLE sales.customers
    ADD CONSTRAINT UQ_customers_email UNIQUE (email);

ALTER TABLE sales.customers
    ADD CONSTRAINT CK_customers_gstin
    CHECK (gstin IS NULL OR LEN(gstin) = 15);         -- optional, but if present must be 15 chars

ALTER TABLE sales.orders
    ADD CONSTRAINT CK_orders_amount CHECK (amount > 0);

-- A multi-column CHECK: discounts can't exceed the amount
ALTER TABLE sales.orders ADD discount DECIMAL(12,2) NOT NULL
    CONSTRAINT DF_orders_discount DEFAULT 0;
ALTER TABLE sales.orders
    ADD CONSTRAINT CK_orders_discount CHECK (discount >= 0 AND discount <= amount);

INSERT INTO sales.orders (customer_id, amount) VALUES (2, -50);    -- fails CK_orders_amount
INSERT INTO sales.customers (full_name, email, city)
VALUES (N'Asha Again', 'asha@example.in', N'Pune');                -- fails UQ_customers_email
""", "03_check_unique.sql", lang="sql")}
{ul(["<b>UNIQUE</b> differs from PK: a table can have many UNIQUE constraints, and a UNIQUE column may allow one NULL row.",
"<b>CHECK</b> sees one row at a time. “Total of all orders &lt; credit limit” is not expressible as a CHECK — that's for triggers, procedures or application code.",
"A CHECK that evaluates to NULL (because a column is NULL) <b>passes</b> — NULL is “unknown”, not “false”. That's why the gstin check spells out <code>IS NULL OR …</code> for clarity.",
"<b>DEFAULT</b> applies only when the column is omitted from the INSERT (or with the keyword <code>DEFAULT</code>) — inserting an explicit NULL does not trigger it."])}

<h3>4. Reading an ER diagram</h3>
{C(r"""
+--------------+ 1       * +-----------+ 1       * +---------------+
|  customers   |-----------|  orders   |-----------|  order_items  |
+--------------+           +-----------+           +---------------+
| customer_id  |           | order_id  |           | order_id   FK |
| full_name    |           | customer  |           | product_id FK |
| email  (UQ)  |           |   _id  FK |           | quantity      |
| city         |           | ordered_on|           | unit_price    |
+--------------+           | amount    |       * \ +---------------+
                           +-----------+          \ 1
                                                +----------+
                                                | products |
                                                +----------+
""", lang="text")}
{table(["Symbol (crow's foot)","Meaning","Example"],[
["1 — *","One-to-many: one parent row, many children","One customer places many orders"],
["1 — 1","One-to-one: usually a split table","employee — employee_login_details"],
["* — *","Many-to-many: needs a junction table in between","students — courses via enrollments; orders — products via order_items"],
["o (circle)","Optional (zero allowed)","An employee may have no manager"]])}
<p>A many-to-many never maps to a single FK — it always becomes a middle table whose composite key (or surrogate key + UNIQUE pair) is the two FKs. You already built one: <code>order_items</code>.</p>

<h3>5. Normalization: a worked example</h3>
<p>Start from the spreadsheet a small shop actually keeps:</p>
{table(["order_id","ordered_on","customer_name","customer_phone","customer_city","items"],[
["5001","2026-11-02","Asha Patel","98200-11111","Mumbai","Rice ×2; Chai ×1"],
["5002","2026-11-02","Ravi Kumar","99100-22222","Delhi","Chai ×3"],
["5003","2026-11-05","Asha Patel","98200-11111","Mumbai","Bulb ×4; Rice ×1"]])}
<h4>1NF — atomic values, no repeating groups</h4>
<p>“Rice ×2; Chai ×1” packs many facts into one cell. Split into one row per order line, and give the table a key — <code>(order_id, product_id)</code>:</p>
{table(["order_id","ordered_on","customer_name","customer_phone","customer_city","product_id","product_name","qty","unit_price"],[
["5001","2026-11-02","Asha Patel","98200-11111","Mumbai","P1","Basmati Rice","2","599.00"],
["5001","2026-11-02","Asha Patel","98200-11111","Mumbai","P2","Masala Chai","1","149.00"],
["5002","2026-11-02","Ravi Kumar","99100-22222","Delhi","P2","Masala Chai","3","149.00"],
["5003","2026-11-05","Asha Patel","98200-11111","Mumbai","P3","LED Bulb","4","99.00"]])}
<h4>2NF — no partial dependencies on a composite key</h4>
<p>With key <code>(order_id, product_id)</code>: <code>product_name</code> depends on <b>product_id alone</b>, and <code>ordered_on</code>/customer columns on <b>order_id alone</b>. Each partial dependency moves to its own table:</p>
{ul(["<code>products(product_id PK, product_name, unit_price)</code>",
"<code>orders(order_id PK, ordered_on, customer_name, customer_phone, customer_city)</code>",
"<code>order_items(order_id FK, product_id FK, qty)</code> — only what depends on the full key stays"])}
<h4>3NF — no transitive dependencies</h4>
<p>In <code>orders</code>, phone and city depend on <i>who the customer is</i>, not on the order: <code>order_id → customer → phone/city</code>. Asha's phone is stored twice and can disagree with itself (an <b>update anomaly</b>). Extract the customer:</p>
{ul(["<code>customers(customer_id PK, full_name, phone, city)</code>",
"<code>orders(order_id PK, customer_id FK, ordered_on)</code>",
"<code>products(product_id PK, product_name, unit_price)</code>",
"<code>order_items(order_id FK, product_id FK, qty, unit_price_at_sale)</code>"])}
<p>Memory hook for 3NF: every non-key column depends on <i>“the key, the whole key, and nothing but the key”</i>. (Insert, update and delete anomalies all trace back to a column that breaks this.)</p>
{tip("Why does <code>order_items</code> keep <code>unit_price_at_sale</code> when products has a price? Because the catalogue price changes and an old invoice must not. That's not a normalization failure — the price <i>at the moment of sale</i> is a genuine fact about the order line. Historical snapshots are correct design.")}

<h3>6. When to denormalize</h3>
{table(["Situation","Denormalization","Cost you accept"],[
["Order total shown in every list screen","Store <code>total_amount</code> on orders instead of summing items each time","Must recompute whenever items change"],
["Report over millions of rows joins 6 tables","A flattened reporting table refreshed nightly","Data is up to a day stale"],
["Customer's city printed on old invoices","Copy city onto the order at purchase time","Two places to look for “city”, with different meanings"],
["Read-heavy product page","Cached counts like <code>review_count</code>","Counter drift; needs careful updating"]])}
{ul(["Default to 3NF for transactional (OLTP) schemas — it keeps every fact in one place, so updates can't disagree.",
"Denormalize for measured read performance or reporting, and write down <i>what</i> is duplicated and <i>what keeps it in sync</i> (trigger, job, application code).",
"Never denormalize to avoid writing a JOIN — Friday makes joins routine."])}
''',
["Forgetting to name constraints, then hunting for <code>PK__orders__C3905BAF…</code> in a migration script.",
"FK column typed <code>BIGINT</code> referencing an <code>INT</code> PK — error before you even start.",
"<code>ON DELETE CASCADE</code> from a lookup table (delete the “Karnataka” row, lose every customer in it).",
"Expecting a CHECK to validate across rows or tables — it can't see beyond the current row.",
"Storing comma-separated lists (phone1,phone2,phone3) instead of a child table — the classic 1NF break."],
("40 min", ["Add proper constraints to yesterday's <code>sales.customers</code>: unique email, CHECK that <code>pin_code</code> is 6 digits (<code>LIKE '[0-9][0-9][0-9][0-9][0-9][0-9]'</code>), default created-at.",
"Create <code>sales.payments(payment_id PK, order_id FK ON DELETE CASCADE, paid_on, amount CHECK &gt; 0, method CHECK IN ('UPI','CARD','COD'))</code>. Verify both the FK error and the cascade by deleting an order.",
"Take this table and normalize it to 3NF on paper: <code>trips(trip_id, bus_no, bus_capacity, driver_name, driver_phone, route_name, departure)</code>. List the final tables, PKs and FKs."]),
[("Why can a UNIQUE column hold a NULL when a PK can't?","A PK identifies rows, so every row must have a real, unique value. UNIQUE merely forbids duplicates among the values present; SQL Server permits exactly one NULL row in a UNIQUE index (stricter than the SQL standard, which allows many)."),
("What does ON DELETE SET NULL require of the child column?","It must be nullable — otherwise there is nothing valid to set, and the constraint is rejected when you create it."),
("A CHECK constraint evaluates to NULL for a row. Is the row rejected?","No. CHECK rejects only rows where the condition is FALSE; NULL ('unknown') passes. That's why CHECK (discount <= amount) doesn't reject rows where discount is NULL.")],
[("Basic","What is the difference between a primary key and a unique constraint?","Both enforce uniqueness via an index. A table has one PK, which allows no NULLs and is the default clustered index and FK target. UNIQUE constraints can be many per table, allow one NULL (in SQL Server), and typically guard natural keys like email while a surrogate PK identifies the row."),
("Basic","What is a foreign key and what problem does it solve?","A column (or columns) constrained to match a PK/UNIQUE value in a referenced table, or be NULL. It guarantees referential integrity: no order can point at a customer that doesn't exist, and a referenced customer can't be deleted (unless a cascade rule says otherwise). It turns 'dangling reference' bugs into immediate, loud errors."),
("Basic","Explain 1NF, 2NF and 3NF in one line each.","1NF: atomic column values, no repeating groups, and a key. 2NF: 1NF plus no column depending on only part of a composite key. 3NF: 2NF plus no column depending on another non-key column (no transitive dependencies). Shorthand: the key, the whole key, nothing but the key."),
("Intermediate","Surrogate vs natural keys — which do you choose and why?","Default to a surrogate (INT IDENTITY): compact, stable, meaningless, so it never changes when business data does. Keep the natural key (email, PAN, ISBN) as a UNIQUE constraint so its uniqueness is still enforced. Natural keys as PKs cause pain when they change (cascading updates) or turn out not to be unique in the real world."),
("Intermediate","What are insert, update and delete anomalies?","Symptoms of under-normalized tables. Insert anomaly: you can't record a product until someone orders it. Update anomaly: a customer's phone stored on 50 order rows must be changed 50 times, and a miss leaves contradictions. Delete anomaly: deleting the last order of a customer erases the customer's details too. Normalization removes the duplication that causes all three."),
("Intermediate","When is denormalization justified?","When a measured read pattern is too slow or complex and the duplication has a defined sync strategy: precomputed totals maintained transactionally, reporting tables refreshed on a schedule, or point-in-time snapshots like price-at-sale (which is really historical accuracy, not redundancy). It's a performance trade accepted consciously — never the starting design.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "SELECT: filtering, LIKE, NULLs, ORDER BY and paging",
"Query data with confidence: predicates, pattern matching, NULL-safe conditions, sorting, TOP and OFFSET-FETCH paging — and the logical order the engine actually follows.",
[("SELECT","The statement that reads data. You list columns (the projection) and where they come from."),
("Predicate","A condition that's TRUE, FALSE or UNKNOWN for each row: <code>price &lt; 500</code>. WHERE keeps only TRUE rows."),
("Comparison operators","<code>=</code>, <code>&lt;&gt;</code> (or <code>!=</code>), <code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code>, <code>&gt;=</code>."),
("LIKE","Pattern match for text: <code>%</code> any run of characters, <code>_</code> exactly one, <code>[abc]</code>/<code>[0-9]</code> a set or range, <code>[^…]</code> negation."),
("IN","Shorthand for a list of equalities: <code>city IN (N'Pune', N'Mumbai')</code>."),
("BETWEEN","Inclusive range: <code>price BETWEEN 100 AND 600</code> includes both ends."),
("IS NULL / IS NOT NULL","The only correct way to test for NULL. <code>= NULL</code> never matches anything."),
("Three-valued logic","With NULLs, conditions can be TRUE, FALSE or UNKNOWN; WHERE and CHECK treat UNKNOWN differently (WHERE drops it, CHECK lets it pass)."),
("ORDER BY","Sorts the final result. Without it, row order is an accident of the execution plan — never rely on it."),
("TOP (n)","T-SQL's way to cap the row count; <code>WITH TIES</code> includes rows tied with the last one."),
("OFFSET … FETCH","Standard paging attached to ORDER BY: skip N rows, return the next M."),
("DISTINCT","Removes duplicate rows from the projected columns."),
("Column alias","A rename for output: <code>price * 1.18 AS price_with_gst</code>. Assigned late — WHERE can't see it."),
("Logical query processing","The order the engine evaluates clauses: FROM → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → TOP/OFFSET.")],
["Write the column list explicitly; <code>SELECT *</code> is for exploring, not for code.",
"Text literals for NVARCHAR columns get the <code>N</code> prefix: <code>N'Pune'</code>.",
"NULL never equals anything, including NULL — use <code>IS NULL</code>.",
"AND binds tighter than OR; parenthesise as soon as you mix them.",
"TOP and OFFSET-FETCH are only meaningful with ORDER BY.",
"Default collations are case-insensitive: <code>WHERE name = 'asha'</code> matches 'Asha'."],
f'''
<h3>1. Today's demo table</h3>
{C(r"""
USE CompanyDb;
GO
CREATE TABLE dbo.products
(
    product_id   INT           NOT NULL CONSTRAINT PK_products PRIMARY KEY,
    name         NVARCHAR(60)  NOT NULL,
    category     NVARCHAR(30)  NOT NULL,
    price        DECIMAL(10,2) NOT NULL,
    stock        INT           NULL,          -- NULL = stock not yet counted
    discontinued BIT           NOT NULL,
    launched     DATE          NOT NULL
);

INSERT INTO dbo.products VALUES
(1,  N'Basmati Rice 5kg',   N'Grocery',    599.00, 120,  0, '2024-03-01'),
(2,  N'Masala Chai 250g',   N'Grocery',    149.00, 200,  0, '2023-06-15'),
(3,  N'LED Bulb 9W',        N'Electrical',  99.00, 500,  0, '2022-01-10'),
(4,  N'Mixer Grinder 750W', N'Appliances', 3499.00, 35,  0, '2024-08-20'),
(5,  N'Pressure Cooker 5L', N'Appliances', 2199.00,  0,  0, '2021-11-05'),
(6,  N'Notebook A4 200pg',  N'Stationery',  60.00, 350,  0, '2020-04-18'),
(7,  N'Gel Pen Blue',       N'Stationery',  20.00, 1000, 0, '2019-07-01'),
(8,  N'USB-C Cable 1m',     N'Electronics', 299.00, 80,  0, '2023-02-25'),
(9,  N'CRT TV 21in',        N'Electronics', 4999.00, 2,  1, '2015-01-01'),
(10, N'Smart Watch Pro',    N'Electronics', 6999.00, NULL, 0, '2025-09-12');
""", "00_setup_products.sql", lang="sql")}

<h3>2. FROM, WHERE and operators</h3>
{C(r"""
SELECT product_id, name, price
FROM dbo.products
WHERE category = N'Electronics' AND price < 5000;
""", lang="sql")}
{C(r"""
product_id  name            price
----------- --------------- --------
8           USB-C Cable 1m  299.00
9           CRT TV 21in     4999.00
(2 rows affected)
""", lang="text")}
{C(r"""
-- AND binds tighter than OR. These two are DIFFERENT queries:
SELECT name FROM dbo.products
WHERE category = N'Grocery' OR category = N'Stationery' AND price < 50;
-- means: Grocery OR (Stationery AND price < 50) → all grocery + only the pen

SELECT name FROM dbo.products
WHERE (category = N'Grocery' OR category = N'Stationery') AND price < 50;
-- → only Gel Pen Blue (20.00)

SELECT name, stock FROM dbo.products WHERE NOT discontinued = 1;   -- or: discontinued = 0
""", lang="sql")}
{tip("Read a query in execution order, not written order: <b>FROM</b> grabs the table, <b>WHERE</b> filters rows, <b>SELECT</b> projects columns. That mental model answers most “why doesn't this work” questions.")}

<h3>3. LIKE, IN and BETWEEN</h3>
{C(r"""
SELECT name FROM dbo.products WHERE name LIKE N'%Pen%';      -- contains "Pen"
SELECT name FROM dbo.products WHERE name LIKE N'_asala%';    -- _ = exactly one char → Masala Chai 250g
SELECT name FROM dbo.products WHERE category LIKE N'Electr%';-- Electrical + Electronics
SELECT name FROM dbo.products WHERE name LIKE N'[BG]%';      -- starts with B or G
SELECT name FROM dbo.products WHERE name LIKE N'%[0-9]kg%';  -- a digit before "kg" → Basmati Rice 5kg

-- Escaping a literal % or _ :
-- WHERE code LIKE '50!%%' ESCAPE '!'        → codes starting with "50%"

SELECT name, price FROM dbo.products
WHERE category IN (N'Grocery', N'Stationery');               -- 4 rows: 1, 2, 6, 7

SELECT name, price FROM dbo.products
WHERE price BETWEEN 100 AND 600                              -- inclusive: 100 <= price <= 600
ORDER BY price;
""", "01_like_in_between.sql", lang="sql")}
{C(r"""
name              price
----------------- -------
Masala Chai 250g  149.00
USB-C Cable 1m    299.00
Basmati Rice 5kg  599.00
(3 rows affected)
""", lang="text")}
{warn("A leading wildcard (<code>LIKE '%cable%'</code>) can't use an index on that column — fine on 10 rows, a table scan on 10 million. Park the thought until index week; just remember prefix searches (<code>LIKE 'USB%'</code>) are the fast kind.", "Note")}

<h3>4. NULL and three-valued logic</h3>
{C(r"""
SELECT name, stock FROM dbo.products WHERE stock = NULL;     -- 0 rows. ALWAYS.
SELECT name, stock FROM dbo.products WHERE stock IS NULL;    -- Smart Watch Pro
SELECT name FROM dbo.products WHERE stock IS NOT NULL AND stock < 50;  -- Mixer (35), Cooker (0), CRT TV (2)

-- Why: any comparison with NULL is UNKNOWN, and WHERE keeps only TRUE rows.
-- Even NULL = NULL is UNKNOWN ("is one unknown thing equal to another? unknown").

-- Replacing NULL for display:
SELECT name,
       ISNULL(stock, 0)        AS stock_or_zero,     -- T-SQL, 2 args
       COALESCE(stock, 0)      AS stock_coalesce     -- standard, n args, better type rules
FROM dbo.products
WHERE product_id = 10;
""", "02_nulls.sql", lang="sql")}
{C(r"""
name             stock_or_zero  stock_coalesce
---------------- -------------- --------------
Smart Watch Pro  0              0
""", lang="text")}
<p>Watch the trap in negative conditions: <code>WHERE stock &lt;&gt; 100</code> does <b>not</b> return the Smart Watch — its stock is UNKNOWN, and UNKNOWN isn't TRUE. If NULLs should count as “not 100”, write <code>WHERE stock &lt;&gt; 100 OR stock IS NULL</code>.</p>

<h3>5. ORDER BY, TOP and OFFSET-FETCH</h3>
{C(r"""
-- Three most expensive products
SELECT TOP (3) name, price
FROM dbo.products
ORDER BY price DESC;
""", lang="sql")}
{C(r"""
name               price
------------------ --------
Smart Watch Pro    6999.00
CRT TV 21in        4999.00
Mixer Grinder 750W 3499.00
""", lang="text")}
{C(r"""
-- Multi-key sort: category A→Z, then price high→low inside each category
SELECT category, name, price
FROM dbo.products
ORDER BY category ASC, price DESC;

-- TOP (1) WITH TIES: all products sharing the top price would come along
SELECT TOP (1) WITH TIES name, price
FROM dbo.products
ORDER BY price DESC;

-- Paging, page 2 with 3 rows per page (rows 4-6 in product_id order):
SELECT product_id, name
FROM dbo.products
ORDER BY product_id
OFFSET 3 ROWS FETCH NEXT 3 ROWS ONLY;
""", "03_order_top_paging.sql", lang="sql")}
{C(r"""
product_id  name
----------- ------------------
4           Mixer Grinder 750W
5           Pressure Cooker 5L
6           Notebook A4 200pg
""", lang="text")}
{warn("OFFSET-FETCH requires an ORDER BY, and the ORDER BY must be deterministic (unique) for stable pages — sort by price alone and two 149.00 products could swap between page loads. Add the PK as a tiebreaker: <code>ORDER BY price DESC, product_id</code>.", "Gotcha")}

<h3>6. DISTINCT, aliases, and the logical processing order</h3>
{C(r"""
SELECT DISTINCT category FROM dbo.products ORDER BY category;
-- Appliances, Electrical, Electronics, Grocery, Stationery   (5 rows)

-- Aliases: rename output, compute columns
SELECT name                    AS product,
       price                   AS base_price,
       CAST(price * 1.18 AS DECIMAL(10,2)) AS price_with_gst   -- 18% GST
FROM dbo.products
WHERE category = N'Appliances';

-- ❌ Why this FAILS: "Invalid column name 'price_with_gst'"
SELECT name, price * 1.18 AS price_with_gst
FROM dbo.products
WHERE price_with_gst > 1000;        -- WHERE runs BEFORE SELECT names it

-- ✓ Repeat the expression (or use a derived table/CTE — Week 12)
SELECT name, price * 1.18 AS price_with_gst
FROM dbo.products
WHERE price * 1.18 > 1000;

-- ORDER BY runs AFTER SELECT, so IT can use the alias:
SELECT name, price * 1.18 AS price_with_gst
FROM dbo.products
ORDER BY price_with_gst DESC;
""", "04_distinct_aliases.sql", lang="sql")}
{table(["Step","Clause","What it does"],[
["1","FROM (+ JOINs)","Builds the working set of rows"],
["2","WHERE","Filters rows (no aliases, no aggregates)"],
["3","GROUP BY","Collapses rows into groups (Week 12)"],
["4","HAVING","Filters groups (Week 12)"],
["5","SELECT","Projects columns, computes expressions, assigns aliases"],
["6","DISTINCT","Removes duplicate result rows"],
["7","ORDER BY","Sorts (can use aliases)"],
["8","TOP / OFFSET-FETCH","Cuts the final window"]])}
<p>This one table explains the two most common beginner errors — aliases in WHERE, and expecting rows in a particular order without ORDER BY.</p>
''',
["<code>= NULL</code> instead of <code>IS NULL</code> — silently returns nothing.",
"Mixing AND/OR without parentheses and filtering the wrong rows.",
"Using a column alias in WHERE (it doesn't exist yet at that step).",
"Paging with a non-deterministic ORDER BY — rows repeat or vanish across pages.",
"<code>SELECT *</code> in application code: breaks when columns change, drags unneeded bytes over the wire."],
("40 min", ["Write queries against <code>dbo.products</code> for: all non-discontinued Electronics under ₹5,000; products whose name contains a digit; products launched between 2022-01-01 and 2024-12-31 sorted newest first.",
"Products with unknown stock OR stock below 50, showing <code>ISNULL(stock, -1)</code>; explain in a comment why <code>stock &lt; 50</code> alone misses a row.",
"Page through all 10 products 4 at a time with OFFSET-FETCH (3 queries), ordered by price DESC with product_id as tiebreaker. Verify no product repeats across pages."]),
[("Why does WHERE price_with_gst > 1000 fail when the alias is right there in SELECT?","Logical processing order: WHERE is evaluated before SELECT, so the alias hasn't been created yet. Repeat the expression in WHERE, or wrap the query in a derived table/CTE that makes the alias a real column."),
("What does BETWEEN 100 AND 600 include?","Both endpoints: price >= 100 AND price <= 600. For half-open ranges (common with dates) write the comparisons explicitly: ordered_on >= '2026-01-01' AND ordered_on < '2027-01-01'."),
("Is the result order guaranteed without ORDER BY?","No. Rows come back in whatever order the execution plan produced them — often the clustered index today, something else after an index or plan change. If order matters, say so with ORDER BY.")],
[("Basic","Explain the logical order of query processing and why it matters.","FROM → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → TOP/OFFSET. It explains why WHERE can't use SELECT aliases or aggregates, why HAVING exists separately from WHERE, and why ORDER BY can use aliases. Written order is for humans; logical order is how the engine resolves the query."),
("Basic","What LIKE wildcards does SQL Server support?","% matches any string of zero or more characters, _ matches exactly one character, [abc] and [0-9] match one character from a set or range, [^abc] matches one character NOT in the set. Literal % or _ are matched via ESCAPE or by wrapping in brackets: LIKE '50[%]'."),
("Basic","How do you test for NULL and why doesn't = NULL work?","With IS NULL / IS NOT NULL. Any comparison involving NULL evaluates to UNKNOWN (not TRUE, not FALSE) under three-valued logic, and WHERE only keeps TRUE rows — so col = NULL filters everything out, without an error."),
("Intermediate","What's the difference between ISNULL and COALESCE?","ISNULL(a, b) is T-SQL only, takes exactly two arguments, and the result type comes from the first argument (which can truncate the replacement). COALESCE is ANSI standard, takes any number of arguments, returns the first non-NULL, and picks the result type by data-type precedence across all arguments. Prefer COALESCE for portability and multi-fallback chains."),
("Intermediate","How do you implement stable paging in SQL Server?","ORDER BY a deterministic key (add the PK as a tiebreaker), then OFFSET (page-1)*size ROWS FETCH NEXT size ROWS ONLY. Note that big offsets still read and discard all skipped rows, so very deep paging is better served by keyset pagination: WHERE key > last-seen-key ORDER BY key."),
("Intermediate","What does TOP (1) WITH TIES do?","It returns the first row per the ORDER BY plus any further rows whose sort-key values equal the last returned row's. TOP (1) WITH TIES ... ORDER BY price DESC returns ALL products sharing the maximum price — a neat way to answer 'the most expensive product(s)' without a subquery. WITH TIES requires ORDER BY.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "INSERT, UPDATE, DELETE, TRUNCATE and MERGE",
"Change data safely: multi-row inserts, INSERT…SELECT, the OUTPUT clause, UPDATE with joins, DELETE vs TRUNCATE, and MERGE with its sharp edges.",
[("DML","Data Manipulation Language: INSERT, UPDATE, DELETE, MERGE (SELECT reads). DDL is CREATE/ALTER/DROP."),
("INSERT … VALUES","Adds rows; one VALUES clause can carry many rows separated by commas."),
("INSERT … SELECT","Inserts the result of a query — copying or transforming existing data."),
("SELECT … INTO","Creates a brand-new table from a query's shape and rows (no constraints copied)."),
("SCOPE_IDENTITY()","The last IDENTITY value generated in your scope — the standard way to get a new row's id."),
("OUTPUT clause","Returns the rows a DML statement touched, via the pseudo-tables <code>inserted</code> and <code>deleted</code>."),
("inserted / deleted","Virtual tables inside DML: new row versions in <code>inserted</code>, old versions in <code>deleted</code> (UPDATE fills both)."),
("UPDATE … FROM","T-SQL extension: update a table using values joined from another table."),
("DELETE","Removes rows (all of them if you forget WHERE), one by one, fully logged, firing triggers."),
("TRUNCATE TABLE","Empties a table by deallocating pages: minimally logged, resets IDENTITY, no WHERE, blocked by any referencing FK."),
("MERGE","One statement that compares a source to a target and INSERTs / UPDATEs / DELETEs accordingly (an “upsert”)."),
("Upsert","Update the row if it exists, insert it if it doesn't."),
("@@ROWCOUNT","How many rows the previous statement affected.")],
["Always list the target columns in INSERT — surviving table changes is worth the typing.",
"Write the WHERE of an UPDATE/DELETE first, test it as a SELECT, then change the verb.",
"OUTPUT beats SCOPE_IDENTITY when you insert many rows at once.",
"TRUNCATE needs no WHERE because it can't take one — it's all or nothing.",
"MERGE has documented gotchas; many teams prefer explicit UPDATE + INSERT.",
"Everything today respects constraints: a CHECK or FK failure rolls the whole statement back."],
f'''
<h3>1. INSERT: multi-row, explicit columns, identity capture</h3>
{C(r"""
USE CompanyDb;
GO
CREATE TABLE sales.coupons
(
    coupon_id  INT IDENTITY(1,1) CONSTRAINT PK_coupons PRIMARY KEY,
    code       VARCHAR(20)   NOT NULL CONSTRAINT UQ_coupons_code UNIQUE,
    discount   DECIMAL(5,2)  NOT NULL CONSTRAINT CK_coupons_discount CHECK (discount BETWEEN 0.5 AND 90),
    valid_till DATE          NOT NULL
);

-- Multi-row insert: one statement, one log entry per row, atomic as a whole
INSERT INTO sales.coupons (code, discount, valid_till) VALUES
('DIWALI25',  25.00, '2026-11-20'),
('NEWUSER10', 10.00, '2027-03-31'),
('CLEAR50',   50.00, '2026-12-31');

SELECT SCOPE_IDENTITY() AS last_id;    -- 3 (the LAST identity this scope generated)
SELECT @@ROWCOUNT       AS rows_hit;   -- 1 (careful: counts the SELECT above, not the INSERT!)
""", "01_insert.sql", lang="sql")}
<p><code>SCOPE_IDENTITY()</code> must be read right after the INSERT, in the same scope — and it only carries the last value, which is why multi-row inserts pair better with OUTPUT (section 3). If any row of a multi-row insert violates a constraint, <b>no</b> rows are inserted: the statement is atomic.</p>

<h3>2. INSERT … SELECT and SELECT … INTO</h3>
{C(r"""
-- Copy query results into an EXISTING table
CREATE TABLE dbo.premium_products
(
    product_id INT           NOT NULL CONSTRAINT PK_premium_products PRIMARY KEY,
    name       NVARCHAR(60)  NOT NULL,
    price      DECIMAL(10,2) NOT NULL
);

INSERT INTO dbo.premium_products (product_id, name, price)
SELECT product_id, name, price
FROM dbo.products
WHERE price >= 2000 AND discontinued = 0;     -- Mixer, Cooker, Smart Watch → 3 rows

-- SELECT INTO: create a NEW table from the query's shape (quick snapshot/backup)
SELECT product_id, name, price, stock
INTO dbo.products_backup_20261113
FROM dbo.products;
-- Column names+types are copied; PKs, FKs, CHECKs, DEFAULTs and IDENTITY-as-key behaviour are NOT.
""", "02_insert_select.sql", lang="sql")}
{tip("<code>SELECT INTO</code> is the one-line “let me snapshot this before I touch it” tool. Make a dated backup table before any risky UPDATE/DELETE, and drop it once you're happy.")}

<h3>3. The OUTPUT clause</h3>
{C(r"""
-- INSERT: see the generated ids immediately (works for many rows, unlike SCOPE_IDENTITY)
INSERT INTO sales.coupons (code, discount, valid_till)
OUTPUT inserted.coupon_id, inserted.code
VALUES ('HOLI15', 15.00, '2027-03-10'),
       ('SUMMER5', 5.00, '2027-05-31');
""", lang="sql")}
{C(r"""
coupon_id   code
----------- --------
4           HOLI15
5           SUMMER5
""", lang="text")}
{C(r"""
-- UPDATE: old and new values side by side — a free audit trail
UPDATE dbo.products
SET price = price * 1.05                       -- 5% price revision
OUTPUT inserted.product_id,
       deleted.price  AS old_price,
       inserted.price AS new_price
WHERE category = N'Grocery';
""", lang="sql")}
{C(r"""
product_id  old_price  new_price
----------- ---------- ----------
1           599.00     628.95
2           149.00     156.45
""", lang="text")}
{C(r"""
-- DELETE: capture what you removed (into a table, for archiving)
DECLARE @removed TABLE (product_id INT, name NVARCHAR(60));

DELETE FROM dbo.products
OUTPUT deleted.product_id, deleted.name INTO @removed
WHERE discontinued = 1;

SELECT * FROM @removed;      -- 9, CRT TV 21in
""", "03_output.sql", lang="sql")}
<p>Mental model: <code>inserted</code> holds rows as they look <i>after</i> the statement, <code>deleted</code> as they looked <i>before</i>. INSERT fills only <code>inserted</code>, DELETE only <code>deleted</code>, UPDATE both.</p>

<h3>4. UPDATE — including with a JOIN</h3>
{C(r"""
-- Plain update (SET several columns at once)
UPDATE dbo.products
SET stock = 150, price = 649.00
WHERE product_id = 1;

-- Update from another table: apply category-level GST rates
CREATE TABLE dbo.category_gst
(
    category NVARCHAR(30) NOT NULL CONSTRAINT PK_category_gst PRIMARY KEY,
    gst_rate DECIMAL(5,2) NOT NULL
);
INSERT INTO dbo.category_gst VALUES
(N'Grocery', 5.00), (N'Electrical', 18.00), (N'Appliances', 28.00),
(N'Stationery', 12.00), (N'Electronics', 18.00);

ALTER TABLE dbo.products ADD gst_rate DECIMAL(5,2) NULL;
GO
UPDATE p
SET p.gst_rate = g.gst_rate
FROM dbo.products AS p
JOIN dbo.category_gst AS g ON g.category = p.category;   -- 10 rows updated

SELECT name, category, gst_rate FROM dbo.products WHERE product_id IN (1, 4, 8);
""", "04_update_join.sql", lang="sql")}
{C(r"""
name                category     gst_rate
------------------- ------------ --------
Basmati Rice 5kg    Grocery      5.00
Mixer Grinder 750W  Appliances   28.00
USB-C Cable 1m      Electronics  18.00
""", lang="text")}
{warn("In UPDATE…FROM, if several source rows join to one target row, the target is updated with an arbitrary one of them — no error, no warning. Make sure the join is one-to-one from the target's point of view (here category_gst has one row per category). The ANSI-standard alternative — a correlated subquery in SET — raises an error on duplicates instead.", "Careful")}

<h3>5. DELETE vs TRUNCATE</h3>
{C(r"""
DELETE FROM sales.coupons WHERE valid_till < '2027-01-01';  -- expired ones: rows 1 and 3
SELECT COUNT(*) AS remaining FROM sales.coupons;            -- 3

DELETE FROM sales.coupons;        -- all rows, logged one by one; identity continues from 5
TRUNCATE TABLE sales.coupons;     -- empties AND resets identity to the seed (next id: 1)
""", lang="sql")}
{table(["","DELETE","TRUNCATE TABLE"],[
["WHERE clause","Yes","No — always every row"],
["Logging","Every row fully logged","Page deallocations only (fast on big tables)"],
["Resets IDENTITY","No — numbering continues","Yes — back to the seed"],
["Fires DELETE triggers","Yes","No"],
["Works with referencing FKs","Yes (row by row, if no children exist)","No — fails if ANY table references this one, even when empty"],
["Can be rolled back in a transaction","Yes","Yes (it's still transactional, despite the myth)"],
["Permissions","DELETE permission","ALTER permission on the table"]])}

<h3>6. MERGE: upserts, and why to be careful</h3>
<p>Classic job: a nightly stock feed arrives; update products we know, insert ones we don't.</p>
{C(r"""
CREATE TABLE dbo.stock_feed            -- what the warehouse sent tonight
(
    product_id INT NOT NULL PRIMARY KEY,
    counted    INT NOT NULL
);
INSERT INTO dbo.stock_feed VALUES (1, 140), (5, 60), (10, 25);

MERGE dbo.products WITH (HOLDLOCK) AS target
USING dbo.stock_feed AS src
    ON target.product_id = src.product_id
WHEN MATCHED THEN
    UPDATE SET target.stock = src.counted
WHEN NOT MATCHED BY TARGET THEN
    INSERT (product_id, name, category, price, stock, discontinued, launched)
    VALUES (src.product_id, N'(pending catalogue entry)', N'Uncategorised',
            0.01, src.counted, 0, CAST(SYSDATETIME() AS DATE))
OUTPUT $action, inserted.product_id, inserted.stock;
""", "05_merge.sql", lang="sql")}
{C(r"""
$action  product_id  stock
-------- ----------- ------
UPDATE   1           140
UPDATE   5           60
UPDATE   10          25
-- (all three ids exist in products, so no INSERT branch fired this run)
""", lang="text")}
<p>There's also <code>WHEN NOT MATCHED BY SOURCE THEN DELETE</code> — “remove target rows the feed no longer mentions” — which makes MERGE a full table synchroniser.</p>
{warn("MERGE caveats, worth repeating in interviews: (1) without <code>HOLDLOCK</code>/<code>SERIALIZABLE</code> two concurrent MERGEs can race and hit duplicate-key errors; (2) it has a long history of edge-case bugs (many fixed, reputation earned); (3) the source must not match one target row twice or you get error 8672; (4) complex MERGEs are hard to read and review. A plain transaction with <code>UPDATE</code> then <code>INSERT … WHERE NOT EXISTS</code> is often the clearer, safer upsert.", "Caveats")}
''',
["Running UPDATE/DELETE without WHERE — no confirmation dialog exists; the statement just runs.",
"Using SCOPE_IDENTITY() after a multi-row insert and losing all ids but the last.",
"Assuming TRUNCATE works on a parent table — any referencing FK blocks it.",
"UPDATE…FROM with a one-to-many join silently picking an arbitrary value.",
"Trusting @@ROWCOUNT after another statement has run in between — read it immediately."],
("40 min", ["Create <code>sales.price_history(product_id, old_price, new_price, changed_on DEFAULT)</code>. Raise all Stationery prices by 10% and use OUTPUT…INTO to log old and new prices into it in the same statement.",
"Copy all discontinued or out-of-stock products into <code>dbo.clearance</code> with INSERT…SELECT, then DELETE them from products — but first write both WHERE clauses as SELECTs to count what you'll touch.",
"Build a one-statement MERGE that upserts <code>dbo.category_gst</code> from a 3-row feed where one category is new and one rate changed. Then rewrite it as UPDATE + INSERT…WHERE NOT EXISTS inside a transaction and decide which version you'd ship."]),
[("Why does OUTPUT beat SCOPE_IDENTITY for multi-row inserts?","SCOPE_IDENTITY returns only the single last identity value in scope. OUTPUT inserted.* streams every inserted row — all ids, in one round trip, and it also works for UPDATE and DELETE."),
("Can TRUNCATE be rolled back?","Yes, inside an explicit transaction — it's minimally logged, not unlogged; SQL Server logs the page deallocations and can undo them. The 'TRUNCATE can't be rolled back' line is a myth (true in some other databases)."),
("What does $action give you in a MERGE's OUTPUT?","A string per affected row — 'INSERT', 'UPDATE' or 'DELETE' — telling you which branch handled it. Handy for logging what a sync actually did.")],
[("Basic","What's the difference between DELETE and TRUNCATE?","DELETE removes rows one at a time, honours WHERE, fires triggers, keeps the identity counter, fully logs each row, and needs DELETE permission. TRUNCATE removes all rows by deallocating pages — much faster on large tables — takes no WHERE, fires no triggers, resets IDENTITY to the seed, needs ALTER permission, and is refused when any foreign key references the table. Both are transactional and can be rolled back."),
("Basic","What is the OUTPUT clause?","A DML clause that returns the affected rows via the inserted and deleted pseudo-tables: new values for INSERT, old for DELETE, both for UPDATE. It can return to the client or INTO a table variable/table, which makes it perfect for capturing generated ids and writing audit rows in the same statement."),
("Basic","How do you insert the result of a query into a table?","INSERT INTO target (cols) SELECT … for an existing table — column count and types must line up. SELECT … INTO new_table FROM … creates a fresh table from the query's shape, copying names, types and rows but not constraints, defaults or indexes."),
("Intermediate","How do you update one table from another in T-SQL?","UPDATE alias SET alias.col = src.col FROM target AS alias JOIN source AS src ON … — T-SQL's UPDATE…FROM extension. Verify the join matches at most one source row per target row, because multiple matches silently apply an arbitrary one. The portable form is UPDATE target SET col = (SELECT … correlated subquery), which errors on multiple matches instead."),
("Intermediate","What are the known problems with MERGE?","Race conditions under concurrency unless you add HOLDLOCK/SERIALIZABLE hints (two sessions can both see 'not matched' and collide); error 8672 when the source matches a target row more than once; a documented history of bugs around triggers, filtered indexes and OUTPUT; and sheer complexity that hides mistakes in review. It's fine for single-threaded ETL; for hot upsert paths many teams use explicit UPDATE/INSERT with appropriate locking."),
("Intermediate","A multi-row INSERT hits a CHECK violation on its 7th row. What's in the table?","Nothing from that statement. A single SQL statement is atomic: the constraint failure rolls back all rows the statement had inserted so far. (The identity counter, however, may still have consumed values — gaps are normal.)")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "JOINs: INNER, OUTER, CROSS, self joins and anti-joins",
"Combine tables confidently: all five join types, the employee→manager self join, multi-table joins, where NULLs bite, and the right way to write “not in that table”.",
[("JOIN","Combining rows from two tables by pairing rows that satisfy a condition (the join predicate)."),
("Join predicate","The ON condition deciding which row pairs belong together, usually FK = PK."),
("INNER JOIN","Only pairs that match survive. Rows with no partner on the other side vanish."),
("LEFT (OUTER) JOIN","Everything from the left table, matched where possible; unmatched left rows get NULLs for the right side."),
("RIGHT (OUTER) JOIN","Mirror image: everything from the right table. Rarely written — most teams reorder tables and use LEFT."),
("FULL (OUTER) JOIN","Everything from both sides; unmatched rows from either side padded with NULLs."),
("CROSS JOIN","Every row paired with every row — the Cartesian product. No ON clause."),
("Self join","A table joined to itself under two aliases — e.g. employees to their managers."),
("Semi-join","“Rows that HAVE a match”, written with EXISTS — no columns from, and no duplicates caused by, the other table."),
("Anti-join","“Rows with NO match”, written with NOT EXISTS (or a LEFT JOIN … IS NULL check)."),
("NOT IN + NULL trap","If the subquery list contains a single NULL, NOT IN returns no rows at all."),
("ON vs WHERE","For INNER joins they filter identically; for OUTER joins, ON decides what matches, WHERE filters the joined result — and can silently undo the OUTER part.")],
["Modern syntax only: <code>JOIN … ON</code>. Comma joins with WHERE are 1989-style.",
"Start from the table you want ALL rows of, and LEFT JOIN the optional data onto it.",
"Alias every table (<code>e</code>, <code>d</code>, <code>m</code>) and qualify every column — mandatory in self joins.",
"An INNER JOIN can both drop rows (no match) and multiply rows (many matches). Know your cardinality.",
"Filter the preserved side in WHERE, the NULL-padded side in ON.",
"For “not in that table”, NOT EXISTS is the NULL-safe default."],
f'''
<h3>1. Today's demo tables</h3>
{C(r"""
USE CompanyDb;
GO
CREATE TABLE dbo.dept
(
    dept_id   INT          NOT NULL CONSTRAINT PK_dept PRIMARY KEY,
    dept_name NVARCHAR(40) NOT NULL,
    city      NVARCHAR(40) NOT NULL
);
CREATE TABLE dbo.emp
(
    emp_id     INT          NOT NULL CONSTRAINT PK_emp PRIMARY KEY,
    emp_name   NVARCHAR(40) NOT NULL,
    dept_id    INT          NULL CONSTRAINT FK_emp_dept REFERENCES dbo.dept (dept_id),
    manager_id INT          NULL CONSTRAINT FK_emp_mgr  REFERENCES dbo.emp (emp_id),
    salary     DECIMAL(10,2) NOT NULL
);
CREATE TABLE dbo.project
(
    project_id   INT          NOT NULL CONSTRAINT PK_project PRIMARY KEY,
    project_name NVARCHAR(50) NOT NULL,
    dept_id      INT          NOT NULL CONSTRAINT FK_project_dept REFERENCES dbo.dept (dept_id)
);

INSERT INTO dbo.dept VALUES
(10, N'Engineering', N'Bengaluru'),
(20, N'Sales',       N'Gurugram'),
(30, N'HR',          N'Mumbai'),
(40, N'R&D',         N'Pune');          -- no employees yet

INSERT INTO dbo.emp VALUES
(1, N'Asha',  10, NULL, 180000),        -- head of Engineering, no manager
(2, N'Ravi',  10, 1,     95000),
(3, N'Meena', 20, 1,     90000),
(4, N'Imran', NULL, 2,   70000),        -- just hired, department not assigned
(5, N'Tara',  30, 1,     85000);

INSERT INTO dbo.project VALUES
(101, N'Payroll Revamp', 30),
(102, N'Mobile App',     10),
(103, N'Website v2',     10);
""", "00_setup_joins.sql", lang="sql")}

<h3>2. INNER JOIN — matches only</h3>
{C(r"""
SELECT e.emp_name, d.dept_name, d.city
FROM dbo.emp AS e
JOIN dbo.dept AS d ON d.dept_id = e.dept_id      -- INNER is the default
ORDER BY e.emp_id;
""", lang="sql")}
{C(r"""
emp_name  dept_name    city
--------- ------------ ----------
Asha      Engineering  Bengaluru
Ravi      Engineering  Bengaluru
Meena     Sales        Gurugram
Tara      HR           Mumbai
(4 rows affected)
""", lang="text")}
<p>Two rows are missing, for two different reasons: <b>Imran</b> (left row with no match — his dept_id is NULL, and NULL matches nothing) and <b>R&amp;D</b> (right row with no match — no employees). INNER JOIN keeps neither.</p>

<h3>3. OUTER joins — keeping the unmatched</h3>
{C(r"""
-- LEFT: every employee, department if known
SELECT e.emp_name, d.dept_name
FROM dbo.emp AS e
LEFT JOIN dbo.dept AS d ON d.dept_id = e.dept_id
ORDER BY e.emp_id;
""", lang="sql")}
{C(r"""
emp_name  dept_name
--------- ------------
Asha      Engineering
Ravi      Engineering
Meena     Sales
Imran     NULL          ← preserved, padded with NULLs
Tara      HR
""", lang="text")}
{C(r"""
-- RIGHT: every department, employees if any (same as swapping tables + LEFT)
SELECT e.emp_name, d.dept_name
FROM dbo.emp AS e
RIGHT JOIN dbo.dept AS d ON d.dept_id = e.dept_id;
-- Asha/Ravi → Engineering, Meena → Sales, Tara → HR, NULL → R&D   (5 rows)

-- FULL: both sides preserved
SELECT e.emp_name, d.dept_name
FROM dbo.emp AS e
FULL JOIN dbo.dept AS d ON d.dept_id = e.dept_id;
-- the 4 matches + (Imran, NULL) + (NULL, R&D)                     (6 rows)
""", lang="sql")}
<h4>The ON vs WHERE trap</h4>
{C(r"""
-- Task: every department, with its Engineering-city employees if any.
-- ❌ Filtering the NULL-padded side in WHERE kills the OUTER behaviour:
SELECT d.dept_name, e.emp_name
FROM dbo.dept AS d
LEFT JOIN dbo.emp AS e ON e.dept_id = d.dept_id
WHERE e.salary > 80000;
-- R&D's row is (R&D, NULL): NULL > 80000 is UNKNOWN → row dropped.
-- The LEFT JOIN just became an INNER JOIN.

-- ✓ Conditions about the OUTER side belong in ON:
SELECT d.dept_name, e.emp_name
FROM dbo.dept AS d
LEFT JOIN dbo.emp AS e ON e.dept_id = d.dept_id AND e.salary > 80000
ORDER BY d.dept_id;
""", "01_on_vs_where.sql", lang="sql")}
{C(r"""
dept_name    emp_name
------------ ---------
Engineering  Asha
Engineering  Ravi
Sales        Meena
HR           Tara
R&D          NULL      ← still here
""", lang="text")}
{warn("Rule of thumb: in a LEFT JOIN, put conditions on the LEFT (preserved) table in WHERE, and conditions on the RIGHT (nullable) table in ON. A WHERE condition on a right-side column that doesn't accept NULL quietly converts your outer join to an inner one — the single most common join bug in code review.", "Remember")}

<h3>4. CROSS JOIN — every combination</h3>
{C(r"""
-- All dept × project pairings (planning grid): 4 depts × 3 projects = 12 rows
SELECT d.dept_name, p.project_name
FROM dbo.dept AS d
CROSS JOIN dbo.project AS p;

-- Legitimate uses: generating calendars (every date × every store),
-- test-data grids, size/colour variants. Accidental use: forgetting ON
-- in old comma syntax — with modern JOIN syntax you can't forget it.
""", lang="sql")}

<h3>5. Self join: employee → manager</h3>
{C(r"""
SELECT e.emp_name  AS employee,
       m.emp_name  AS manager
FROM dbo.emp AS e
LEFT JOIN dbo.emp AS m ON m.emp_id = e.manager_id   -- same table, two aliases
ORDER BY e.emp_id;
""", "02_self_join.sql", lang="sql")}
{C(r"""
employee  manager
--------- --------
Asha      NULL      ← the boss: LEFT JOIN keeps her
Ravi      Asha
Meena     Asha
Imran     Ravi
Tara      Asha
""", lang="text")}
<p>Think of the aliases as two copies of the table: <code>e</code> is “employees being listed”, <code>m</code> is “the same table consulted as the manager directory”. An INNER self join here would silently drop Asha. Variations worth trying: who earns more than their manager (<code>e.salary &gt; m.salary</code>), and pairs sharing a department (<code>e.dept_id = c.dept_id AND e.emp_id &lt; c.emp_id</code> — the &lt; avoids self-pairs and mirrored duplicates).</p>

<h3>6. Joining more than two tables</h3>
{C(r"""
-- Employee → their department → that department's projects
SELECT e.emp_name, d.dept_name, p.project_name
FROM dbo.emp AS e
JOIN dbo.dept    AS d ON d.dept_id = e.dept_id
JOIN dbo.project AS p ON p.dept_id = d.dept_id
ORDER BY e.emp_name, p.project_name;
""", lang="sql")}
{C(r"""
emp_name  dept_name    project_name
--------- ------------ --------------
Asha      Engineering  Mobile App
Asha      Engineering  Website v2
Ravi      Engineering  Mobile App
Ravi      Engineering  Website v2
Tara      HR           Payroll Revamp
(5 rows affected)
""", lang="text")}
<p>Joins chain left to right, each building on the rows so far. Notice the <b>multiplication</b>: Asha appears twice because Engineering has two projects — a 1-to-many join fans rows out. Meena vanished (Sales has no projects: inner join) and Imran too (no department). If the question was “all employees, with projects where they exist”, both joins must be LEFT.</p>

<h3>7. Anti-joins: NOT EXISTS vs NOT IN</h3>
{C(r"""
-- Departments with no employees — three spellings:

-- (a) NOT EXISTS: the recommended anti-join
SELECT d.dept_name
FROM dbo.dept AS d
WHERE NOT EXISTS (SELECT 1 FROM dbo.emp AS e WHERE e.dept_id = d.dept_id);
-- → R&D

-- (b) LEFT JOIN … IS NULL: same result, join-flavoured
SELECT d.dept_name
FROM dbo.dept AS d
LEFT JOIN dbo.emp AS e ON e.dept_id = d.dept_id
WHERE e.emp_id IS NULL;
-- → R&D

-- (c) NOT IN: THE TRAP
SELECT d.dept_name
FROM dbo.dept AS d
WHERE d.dept_id NOT IN (SELECT e.dept_id FROM dbo.emp AS e);
-- → 0 rows. Zero. Not even R&D.
""", "03_anti_joins.sql", lang="sql")}
<p>Why (c) returns nothing: Imran's <code>dept_id</code> is NULL, so the list is <code>(10, 10, 20, NULL, 30)</code>. For R&amp;D the test is <code>40 &lt;&gt; 10 AND 40 &lt;&gt; 20 AND 40 &lt;&gt; 30 AND 40 &lt;&gt; NULL</code> — and <code>40 &lt;&gt; NULL</code> is UNKNOWN, which poisons the whole AND to UNKNOWN. Not TRUE → row dropped. One NULL in the list empties every NOT IN.</p>
{tip("The positive direction is safer: IN with a NULL in the list still finds matches, and EXISTS is a clean semi-join (“employees who have a project in their department”: <code>WHERE EXISTS (SELECT 1 FROM dbo.project p WHERE p.dept_id = e.dept_id)</code>). Habit to build: EXISTS / NOT EXISTS by default; NOT IN only on columns declared NOT NULL.")}
''',
["Filtering a LEFT JOIN's right side in WHERE and wondering where the NULL rows went.",
"NOT IN over a nullable column — one NULL and the query returns nothing.",
"Not noticing row multiplication from a 1-to-many join (sums double, next week's aggregates go wrong).",
"Self join without distinct aliases — SQL Server rejects the ambiguity, or worse, you join to the wrong copy.",
"Writing RIGHT JOINs that reviewers must mentally flip — reorder the FROM and use LEFT."],
("40 min", ["Write all five join types between <code>dbo.emp</code> and <code>dbo.dept</code> and predict each row count before running (4, 5, 5, 6, 20). Explain the two missing rows of the INNER join in a comment.",
"“Every department with its employees earning over ₹80,000, departments without any still listed” — write it wrong (filter in WHERE) and right (filter in ON), and compare outputs.",
"Employees with no project in their department, two ways: NOT EXISTS, and LEFT JOIN…IS NULL. Then break NOT IN by using it and explain the empty result in a comment."]),
[("An INNER JOIN returned fewer rows than the left table has. Why?","Some left rows had no matching right row (unmatched FK or NULL join column) — inner joins drop them. The reverse surprise, MORE rows, means some left rows matched several right rows."),
("When does a LEFT JOIN behave exactly like an INNER JOIN?","When the WHERE clause has a condition on a right-side column that NULL can't satisfy (e.salary > 80000, e.name = '…'). The padded rows fail the filter and vanish — move that condition into ON to keep outer behaviour."),
("Why prefer NOT EXISTS over NOT IN?","NOT EXISTS is NULL-safe: it checks row existence per outer row and ignores NULL semantics in the values. NOT IN compares values, and a single NULL in the subquery result makes every comparison UNKNOWN, returning zero rows — a silent wrong answer, not an error.")],
[("Basic","Explain the join types in one line each.","INNER: only matching pairs. LEFT: all left rows, right side NULL-padded where unmatched. RIGHT: the mirror. FULL: all rows from both sides, padded where unmatched. CROSS: every combination of rows (no ON). Self join: any of the above with the same table under two aliases."),
("Basic","What is a self join and when do you need one?","Joining a table to itself under two aliases, needed when rows relate to other rows of the same table: employee→manager hierarchies, product→replacement-product, flight legs sharing an airport, finding duplicate rows. The aliases make one logical table act as two."),
("Basic","What happens when the join column contains NULL?","NULL matches nothing — not even another NULL — because NULL = NULL is UNKNOWN. In an INNER join such rows disappear; in a LEFT join they survive from the preserved side with NULLs on the other. This is also the root of the NOT IN trap."),
("Intermediate","In an OUTER join, what's the difference between a condition in ON and in WHERE?","ON decides which rows count as matches, before the outer padding is applied — unmatched preserved rows still come back. WHERE filters the final joined result — a predicate a NULL-padded row can't pass removes it, effectively turning the outer join inner. For INNER joins the two placements are equivalent; for OUTER joins they're different queries."),
("Intermediate","How would you find rows in table A with no match in B, and which pattern do you avoid?","NOT EXISTS (SELECT 1 FROM B WHERE B.key = A.key) — the standard anti-join — or LEFT JOIN B … WHERE B.key IS NULL. Avoid NOT IN (SELECT key FROM B) unless B.key is NOT NULL: one NULL in the list makes the predicate UNKNOWN for every row and the query returns nothing."),
("Intermediate","A query joining orders to order_items shows each order's total doubled after someone added a join to shipments. What happened?","Row multiplication: an order with 2 shipments now produces 2 copies of each item row, so any SUM over items counts everything twice. Fix by aggregating items before the join (derived table/CTE), joining shipments separately, or using EXISTS when shipments were only needed as a filter. Always know each join's cardinality before aggregating.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "HR schema: departments, employees, jobs and salary history",
"Build the full HR micro-schema that every remaining SQL week will query: departments, jobs, locations, employees with a manager self-reference, and a salary history audit table.",
[("HR schema","A canonical practice schema: locations → departments → employees → salary_history, with a jobs reference table. It models a small company's org chart."),
("Self-referencing table","A table with a foreign key back to itself — here employees.manager_id → employees.employee_id."),
("Lookup / reference table","A small table of valid values (jobs, departments) that other tables link to rather than storing the string repeatedly."),
("Audit table","A table that records every change — here every salary revision stores the old amount, new amount, effective date and reason."),
("Seed data","A fixed initial dataset that makes a schema queryable immediately, essential for learning and testing."),
("ER description","Informal prose + ASCII diagram describing table relationships before you draw the proper diagram in a tool.")],
["Build the schema first, verify it compiles cleanly, seed it, then run the verification SELECTs.",
"The manager self-reference must be a nullable FK — the top-level CEO has no manager.",
"salary_history stores every revision, not just the current salary; the current salary lives on the employees table too (denormalized for read speed).",
"All Indian names, cities and job titles reflect real-world context — keep them through all future query exercises.",
"Run each CREATE TABLE in its own GO batch so constraint names are unambiguous."],
f'''
<h3>Schema overview</h3>
{C(r"""
-- Relationship map (one-to-many unless noted)
-- hr.locations  (1) → (many) hr.departments
-- hr.jobs       (1) → (many) hr.employees
-- hr.departments(1) → (many) hr.employees
-- hr.employees  (1) → (many) hr.employees      (self: employee → manager)
-- hr.employees  (1) → (many) hr.salary_history
""", lang="text")}

<h3>Step 1 — Create the HR database and schema</h3>
{C(r"""
-- Run once; skip if CompanyDb already exists from earlier this week
IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'CompanyDb')
    CREATE DATABASE CompanyDb;
GO
USE CompanyDb;
GO
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'hr')
BEGIN
    EXEC('CREATE SCHEMA hr AUTHORIZATION dbo');
END
GO
""", "01_hr_setup.sql", lang="sql")}

<h3>Step 2 — Locations</h3>
{C(r"""
CREATE TABLE hr.locations
(
    location_id  INT           NOT NULL CONSTRAINT PK_locations PRIMARY KEY,
    city         NVARCHAR(50)  NOT NULL,
    state        NVARCHAR(50)  NOT NULL,
    country      NVARCHAR(50)  NOT NULL CONSTRAINT DF_locations_country DEFAULT N'India',
    postal_code  CHAR(6)       NULL
                     CONSTRAINT CK_locations_pin CHECK (postal_code IS NULL OR postal_code LIKE '[0-9][0-9][0-9][0-9][0-9][0-9]')
);
GO

INSERT INTO hr.locations (location_id, city, state, postal_code) VALUES
(1001, N'Mumbai',     N'Maharashtra',    '400001'),
(1002, N'Pune',       N'Maharashtra',    '411001'),
(1003, N'Bengaluru',  N'Karnataka',      '560001'),
(1004, N'Hyderabad',  N'Telangana',      '500001'),
(1005, N'Chennai',    N'Tamil Nadu',     '600001'),
(1006, N'Delhi',      N'Delhi',          '110001'),
(1007, N'Kolkata',    N'West Bengal',    '700001');
""", "02_locations.sql", lang="sql")}

<h3>Step 3 — Jobs (reference table)</h3>
{C(r"""
CREATE TABLE hr.jobs
(
    job_id      VARCHAR(10)   NOT NULL CONSTRAINT PK_jobs PRIMARY KEY,
    job_title   NVARCHAR(50)  NOT NULL,
    min_salary  DECIMAL(12,2) NOT NULL,
    max_salary  DECIMAL(12,2) NOT NULL,
    CONSTRAINT CK_jobs_salary CHECK (min_salary > 0 AND max_salary >= min_salary)
);
GO

INSERT INTO hr.jobs VALUES
('ENG_JR',  N'Junior Software Engineer',   400000,   700000),
('ENG_SR',  N'Senior Software Engineer',   700000,  1200000),
('ENG_LEAD',N'Engineering Lead',          1000000,  1800000),
('MGR',     N'Engineering Manager',       1400000,  2500000),
('HR_EXEC', N'HR Executive',               350000,   600000),
('HR_MGR',  N'HR Manager',                 700000,  1200000),
('FIN_ANLT',N'Finance Analyst',            450000,   800000),
('FIN_MGR', N'Finance Manager',            900000,  1500000),
('SALES_EX',N'Sales Executive',            300000,   600000),
('SALES_MGR',N'Sales Manager',             800000,  1400000),
('VP',      N'Vice President',            2000000,  4000000),
('CEO',     N'Chief Executive Officer',   4000000,  8000000);
GO
""", "03_jobs.sql", lang="sql")}

<h3>Step 4 — Departments</h3>
{C(r"""
CREATE TABLE hr.departments
(
    department_id   INT           NOT NULL CONSTRAINT PK_departments PRIMARY KEY,
    department_name NVARCHAR(60)  NOT NULL,
    location_id     INT           NOT NULL
        CONSTRAINT FK_departments_locations REFERENCES hr.locations (location_id),
    manager_id      INT           NULL        -- filled after employees are created
);
GO

INSERT INTO hr.departments (department_id, department_name, location_id) VALUES
(10, N'Engineering',         1003),   -- Bengaluru
(20, N'Human Resources',     1001),   -- Mumbai
(30, N'Finance',             1001),   -- Mumbai
(40, N'Sales',               1006),   -- Delhi
(50, N'Product Management',  1003),   -- Bengaluru
(60, N'Quality Assurance',   1002),   -- Pune
(70, N'DevOps',              1004);   -- Hyderabad
GO
""", "04_departments.sql", lang="sql")}

<h3>Step 5 — Employees (with manager self-reference)</h3>
{C(r"""
CREATE TABLE hr.employees
(
    employee_id   INT           NOT NULL CONSTRAINT PK_employees PRIMARY KEY,
    first_name    NVARCHAR(40)  NOT NULL,
    last_name     NVARCHAR(40)  NOT NULL,
    email         VARCHAR(100)  NOT NULL CONSTRAINT UQ_employees_email UNIQUE,
    phone         VARCHAR(15)   NULL,
    hire_date     DATE          NOT NULL,
    job_id        VARCHAR(10)   NOT NULL
        CONSTRAINT FK_employees_jobs REFERENCES hr.jobs (job_id),
    salary        DECIMAL(12,2) NOT NULL,
    department_id INT           NULL
        CONSTRAINT FK_employees_departments REFERENCES hr.departments (department_id),
    manager_id    INT           NULL
        CONSTRAINT FK_employees_manager REFERENCES hr.employees (employee_id),
    is_active     BIT           NOT NULL CONSTRAINT DF_employees_active DEFAULT 1,
    CONSTRAINT CK_employees_salary CHECK (salary > 0)
);
GO
""", "05_employees_ddl.sql", lang="sql")}
{tip("The manager FK references <code>hr.employees (employee_id)</code> — the same table. This is legal in SQL Server; the row being inserted must already exist (or the manager_id must be NULL). Insert the CEO first with manager_id = NULL, then others can reference him.")}

{C(r"""
-- Insert CEO first (no manager yet)
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(1, N'Vikram',  N'Nair',     'vikram.nair@company.in',    '9820000001', '2015-01-05', 'CEO',      7500000, NULL, NULL);

-- VPs report to CEO (1)
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(2, N'Priya',   N'Sharma',   'priya.sharma@company.in',   '9820000002', '2016-03-15', 'VP',       3200000, 10,   1),
(3, N'Arjun',   N'Mehta',    'arjun.mehta@company.in',    '9820000003', '2017-06-01', 'VP',       3000000, 20,   1);

-- Engineering managers / leads (report to Priya, emp 2)
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(4, N'Meera',   N'Krishnan', 'meera.krishnan@company.in', '9820000004', '2017-09-10', 'MGR',      1800000, 10,   2),
(5, N'Rahul',   N'Desai',    'rahul.desai@company.in',    '9820000005', '2018-04-01', 'ENG_LEAD', 1400000, 10,   4),
(6, N'Ananya',  N'Pillai',   'ananya.pillai@company.in',  '9820000006', '2018-07-15', 'ENG_LEAD', 1350000, 60,   4);

-- Senior engineers (report to Rahul, emp 5)
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(7,  N'Kiran',   N'Bhat',     'kiran.bhat@company.in',     '9820000007', '2019-02-14', 'ENG_SR',  950000, 10,   5),
(8,  N'Sneha',   N'Joshi',    'sneha.joshi@company.in',    '9820000008', '2019-08-20', 'ENG_SR',  920000, 10,   5),
(9,  N'Aditya',  N'Rao',      'aditya.rao@company.in',     '9820000009', '2020-01-10', 'ENG_SR',  880000, 60,   6),
(10, N'Deepa',   N'Nambiar',  'deepa.nambiar@company.in',  '9820000010', '2020-03-01', 'ENG_SR',  860000, 10,   5);

-- Junior engineers
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(11, N'Suresh',  N'Iyengar',  'suresh.iyengar@company.in', '9820000011', '2021-07-01', 'ENG_JR',  520000, 10,   7),
(12, N'Pooja',   N'Kulkarni', 'pooja.kulkarni@company.in', '9820000012', '2021-09-15', 'ENG_JR',  500000, 60,   6),
(13, N'Nikhil',  N'Verma',    'nikhil.verma@company.in',   '9820000013', '2022-01-10', 'ENG_JR',  480000, 10,   8),
(14, N'Riya',    N'Kapoor',   'riya.kapoor@company.in',    '9820000014', '2022-06-01', 'ENG_JR',  470000, 60,   9),
(15, N'Tanvi',   N'Ghosh',    'tanvi.ghosh@company.in',    '9820000015', '2023-02-15', 'ENG_JR',  460000, 70,   6);

-- HR department (report to Arjun, emp 3)
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(16, N'Kavita',  N'Patel',    'kavita.patel@company.in',   '9820000016', '2017-11-20', 'HR_MGR',  950000, 20,   3),
(17, N'Rohit',   N'Pandey',   'rohit.pandey@company.in',   '9820000017', '2019-05-01', 'HR_EXEC', 480000, 20,  16),
(18, N'Swati',   N'Mishra',   'swati.mishra@company.in',   '9820000018', '2020-10-15', 'HR_EXEC', 460000, 20,  16),
(19, N'Amit',    N'Singh',    'amit.singh@company.in',     '9820000019', '2022-03-01', 'HR_EXEC', 420000, 20,  16);

-- Finance
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(20, N'Nisha',   N'Agarwal',  'nisha.agarwal@company.in',  '9820000020', '2016-08-10', 'FIN_MGR', 1200000, 30,  1),
(21, N'Gaurav',  N'Tiwari',   'gaurav.tiwari@company.in',  '9820000021', '2018-12-01', 'FIN_ANLT', 650000, 30, 20),
(22, N'Pallavi', N'Jain',     'pallavi.jain@company.in',   '9820000022', '2020-07-15', 'FIN_ANLT', 580000, 30, 20);

-- Sales
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(23, N'Vishal',  N'Reddy',    'vishal.reddy@company.in',   '9820000023', '2018-02-01', 'SALES_MGR',1100000, 40,  1),
(24, N'Anjali',  N'Chopra',   'anjali.chopra@company.in',  '9820000024', '2019-11-15', 'SALES_EX',  450000, 40, 23),
(25, N'Manish',  N'Shah',     'manish.shah@company.in',    '9820000025', '2020-04-10', 'SALES_EX',  420000, 40, 23),
(26, N'Ritika',  N'Sinha',    'ritika.sinha@company.in',   '9820000026', '2021-08-20', 'SALES_EX',  400000, 40, 23);

-- Product & DevOps
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, phone, hire_date, job_id, salary, department_id, manager_id)
VALUES
(27, N'Siddharth',N'Nayak',   'siddharth.nayak@company.in','9820000027', '2019-03-01', 'MGR',      1600000, 50,   2),
(28, N'Ishaan',  N'Mukherjee','ishaan.mukherjee@company.in','9820000028','2020-09-01', 'ENG_SR',   900000, 70,  27),
(29, N'Bhavna',  N'Hegde',    'bhavna.hegde@company.in',   '9820000029', '2021-01-15', 'ENG_SR',   880000, 50,  27),
(30, N'Chetan',  N'Kulkarni', 'chetan.kulkarni@company.in','9820000030', '2022-11-01', 'ENG_JR',   490000, 70,  28);
GO
""", "06_employees_seed.sql", lang="sql")}

<h3>Step 6 — Set department managers and add the FK</h3>
{C(r"""
-- Now that employees exist, point each department to its senior person
UPDATE hr.departments SET manager_id = 2  WHERE department_id = 10;   -- Priya
UPDATE hr.departments SET manager_id = 3  WHERE department_id = 20;   -- Arjun
UPDATE hr.departments SET manager_id = 20 WHERE department_id = 30;   -- Nisha
UPDATE hr.departments SET manager_id = 23 WHERE department_id = 40;   -- Vishal
UPDATE hr.departments SET manager_id = 27 WHERE department_id = 50;   -- Siddharth
UPDATE hr.departments SET manager_id = 4  WHERE department_id = 60;   -- Meera
UPDATE hr.departments SET manager_id = 28 WHERE department_id = 70;   -- Ishaan

-- Now safe to add the FK (the values already satisfy it)
ALTER TABLE hr.departments
    ADD CONSTRAINT FK_departments_manager
        FOREIGN KEY (manager_id) REFERENCES hr.employees (employee_id);
GO
""", "07_dept_manager_fk.sql", lang="sql")}
{warn("Add FKs that create circular references AFTER inserting data, not before. Here departments.manager_id → employees.department_id → departments would form a cycle; SQL Server allows circular FKs but blocks ON DELETE CASCADE on them (error 1785).", "Design note")}

<h3>Step 7 — Salary history (audit table)</h3>
{C(r"""
CREATE TABLE hr.salary_history
(
    history_id    INT           NOT NULL CONSTRAINT PK_salary_history PRIMARY KEY IDENTITY(1,1),
    employee_id   INT           NOT NULL
        CONSTRAINT FK_salary_history_emp REFERENCES hr.employees (employee_id),
    old_salary    DECIMAL(12,2) NOT NULL,
    new_salary    DECIMAL(12,2) NOT NULL,
    change_date   DATE          NOT NULL CONSTRAINT DF_salary_history_date DEFAULT CAST(SYSDATETIME() AS DATE),
    changed_by    NVARCHAR(80)  NOT NULL,
    reason        NVARCHAR(200) NULL,
    CONSTRAINT CK_salary_history_amounts CHECK (old_salary > 0 AND new_salary > 0)
);
GO

-- Record initial hires as the first revision (from 0 to hire salary)
INSERT INTO hr.salary_history (employee_id, old_salary, new_salary, change_date, changed_by, reason)
SELECT employee_id, 0.01, salary, hire_date, N'HR System', N'Initial hire'
FROM hr.employees;

-- A round of appraisals in 2024
INSERT INTO hr.salary_history (employee_id, old_salary, new_salary, change_date, changed_by, reason)
SELECT employee_id,
       salary             AS old_salary,
       CAST(salary * 1.10 AS DECIMAL(12,2)) AS new_salary,
       '2024-04-01',
       N'Kavita Patel',
       N'Annual appraisal 2024 - 10% increment'
FROM hr.employees
WHERE job_id IN ('ENG_JR', 'ENG_SR', 'HR_EXEC', 'SALES_EX', 'FIN_ANLT');

-- Apply those raises to the main table
UPDATE e
SET e.salary = sh.new_salary
FROM hr.employees AS e
JOIN hr.salary_history AS sh
    ON sh.employee_id = e.employee_id
   AND sh.reason = N'Annual appraisal 2024 - 10% increment';
GO
""", "08_salary_history.sql", lang="sql")}

<h3>Step 8 — Verification SELECTs with expected output</h3>
{C(r"""
-- 1. How many employees per department?
SELECT d.department_name, COUNT(e.employee_id) AS headcount
FROM hr.departments AS d
LEFT JOIN hr.employees AS e ON e.department_id = d.department_id
GROUP BY d.department_name
ORDER BY headcount DESC;
""", lang="sql")}
{C(r"""
department_name     headcount
------------------- ---------
Engineering         9
Sales               4
Human Resources     4
Quality Assurance   4
Finance             3
Product Management  3
DevOps              3
(7 rows)
""", lang="text")}
{C(r"""
-- 2. Each employee with their manager's name
SELECT e.first_name + N' ' + e.last_name AS employee,
       j.job_title,
       d.department_name,
       ISNULL(m.first_name + N' ' + m.last_name, N'(no manager)') AS manager
FROM hr.employees AS e
JOIN hr.jobs        AS j ON j.job_id        = e.job_id
JOIN hr.departments AS d ON d.department_id = e.department_id
LEFT JOIN hr.employees AS m ON m.employee_id = e.manager_id
ORDER BY d.department_name, e.salary DESC;
""", lang="sql")}
{C(r"""
employee           job_title                  department_name  manager
------------------ -------------------------- ---------------- ------------------
Priya Sharma       Vice President             Engineering      Vikram Nair
Meera Krishnan     Engineering Manager        Engineering      Priya Sharma
Rahul Desai        Engineering Lead           Engineering      Meera Krishnan
Kiran Bhat         Senior Software Engineer   Engineering      Rahul Desai
...  (30 rows total)
""", lang="text")}
{C(r"""
-- 3. Jobs where current salary is outside band (should be 0 for a healthy setup)
SELECT e.first_name + N' ' + e.last_name AS employee, j.job_title,
       e.salary, j.min_salary, j.max_salary
FROM hr.employees AS e
JOIN hr.jobs AS j ON j.job_id = e.job_id
WHERE e.salary < j.min_salary OR e.salary > j.max_salary;
""", lang="sql")}
{C(r"""
(0 rows affected)   -- all salaries within band; initial hire values used 0.01 as old_salary,
                    -- not a real salary, so old_salary < min_salary only in salary_history, not employees
""", lang="text")}
{C(r"""
-- 4. Salary history for a single employee
SELECT sh.change_date, sh.old_salary, sh.new_salary,
       sh.new_salary - sh.old_salary AS delta, sh.reason
FROM hr.salary_history AS sh
WHERE sh.employee_id = 7      -- Kiran Bhat
ORDER BY sh.change_date;
""", lang="sql")}
{C(r"""
change_date  old_salary  new_salary  delta     reason
-----------  ----------  ----------  --------  --------------------------------
2019-02-14   0.01        950000.00   949999.99 Initial hire
2024-04-01   950000.00   1045000.00  95000.00  Annual appraisal 2024 - 10% increment
(2 rows)
""", lang="text")}

<h3>Stretch goals</h3>
<ul>
<li>Add a <code>hr.dependents (dependent_id, employee_id FK, name, relationship, dob)</code> table with 10–15 rows.</li>
<li>Add a <code>hr.projects</code> table and a many-to-many <code>hr.project_assignments</code> junction table.</li>
<li>Write a query that shows each department's total payroll and average salary alongside the company-wide average.</li>
<li>Try to insert an employee with a salary outside the job band and confirm it doesn't fire (CHECK is on the jobs table, not on employees directly — that's a gap; add a CHECK or trigger to close it).</li>
</ul>
''',
iqs=[
("Basic","Why is the manager_id column nullable on the employees table?","The top of the hierarchy (CEO or single owner) has no manager. A nullable FK allows the value to be absent without pointing at a fake sentinel row. All other employees must have a manager_id once the company is properly modelled — an application business rule, not a database constraint (you'd use a trigger or CHECK to enforce 'everyone except CEO must have a manager')."),
("Basic","Why store salary on both employees and salary_history?","Denormalization for read speed: the current salary lives on the row so every query doesn't need to aggregate history. salary_history records all revisions for auditability. The tradeoff is that updates must keep both in sync — which the seed script does explicitly with an UPDATE after each appraisal batch."),
("Intermediate","There is a potential circular foreign key between departments (manager_id → employees) and employees (department_id → departments). How did we handle it?","By inserting departments first without the manager_id FK, then adding the FK constraint after employees were inserted. The circular dependency only matters during inserts and alters; at query time it's just two normal FKs. SQL Server blocks CASCADE DELETE on circular paths but plain RESTRICT/NO ACTION FK pairs are fine."),
("Intermediate","How would you evolve this schema to support employees belonging to multiple departments?","Replace the single employees.department_id column with a junction table: hr.employee_departments (employee_id FK, department_id FK, is_primary BIT, effective_date) with a composite PK. Then make department_id on hr.employees nullable (or remove it) and join through the junction table. The junction lets you model matrix organisations, project-based assignments and department transfers with start/end dates.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Ten practice queries, git setup and Week 11 revision",
"Write and explain 10 progressively harder HR queries, organise your SQL scripts in a git repository, and close the week with a checklist, quiz and next-week preview.",
[("Query decomposition","Breaking a complex question into steps: FROM → JOIN → WHERE → GROUP BY → ORDER BY, then verify one step at a time."),
("Expected output check","Running a query and comparing to a hand-counted expectation; mismatch reveals a logic error."),
("Git for SQL","A repository of numbered .sql files is the simplest way to version schema and seed scripts; use it like any other codebase."),
("Revision checklist","A list of this week's topics with green/amber/red self-assessment; reds go on a flashcard pile.")],
["For each query, write what you expect first — even just a row count — then verify.",
"Work through queries in a fresh session (<code>USE CompanyDb; GO</code>) so there's no ambient state.",
"If a query returns a surprising result, roll back through the execution order: FROM → JOIN → WHERE → SELECT.",
"Push your scripts to GitHub tonight; every remaining SQL week adds to the same repo."],
f'''
<h3>The 10 practice queries</h3>
<p>All queries run against the HR schema built yesterday. Expected outputs are based on the 30-employee seed dataset.</p>

<h4>Q1. All employees in Engineering, sorted by salary descending</h4>
{C(r"""
SELECT e.employee_id,
       e.first_name + N' ' + e.last_name AS full_name,
       e.salary,
       j.job_title
FROM hr.employees AS e
JOIN hr.jobs        AS j ON j.job_id        = e.job_id
JOIN hr.departments AS d ON d.department_id = e.department_id
WHERE d.department_name = N'Engineering'
ORDER BY e.salary DESC;
""", "q01_engineering_by_salary.sql", lang="sql")}
{C(r"""
employee_id  full_name         salary      job_title
-----------  ---------------- ----------  --------------------------
2            Priya Sharma     3200000.00  Vice President
4            Meera Krishnan   1800000.00  Engineering Manager
5            Rahul Desai      1400000.00  Engineering Lead
7            Kiran Bhat       1045000.00  Senior Software Engineer   (post-appraisal)
8            Sneha Joshi      1012000.00  Senior Software Engineer
10           Deepa Nambiar     946000.00  Senior Software Engineer
11           Suresh Iyengar    572000.00  Junior Software Engineer
13           Nikhil Verma      528000.00  Junior Software Engineer
15           Tanvi Ghosh       506000.00  Junior Software Engineer   (dept 70 → DevOps but reports to Ananya)
(9 rows)
""", lang="text")}

<h4>Q2. Each department's headcount, total payroll and average salary</h4>
{C(r"""
SELECT d.department_name,
       COUNT(e.employee_id)              AS headcount,
       SUM(e.salary)                     AS total_payroll,
       CAST(AVG(e.salary) AS DECIMAL(12,2)) AS avg_salary
FROM hr.departments AS d
LEFT JOIN hr.employees AS e ON e.department_id = d.department_id
GROUP BY d.department_name
ORDER BY total_payroll DESC;
""", "q02_dept_payroll.sql", lang="sql")}
{C(r"""
department_name     headcount  total_payroll  avg_salary
-------------------  ---------  -------------  ----------
Engineering          9          11729000.00    1303222.22
...
(7 rows; Engineering highest payroll due to VP and manager)
""", lang="text")}

<h4>Q3. Employees who earn more than their direct manager</h4>
{C(r"""
SELECT e.first_name + N' ' + e.last_name AS employee,
       e.salary                          AS emp_salary,
       m.first_name + N' ' + m.last_name AS manager,
       m.salary                          AS mgr_salary
FROM hr.employees AS e
JOIN hr.employees AS m ON m.employee_id = e.manager_id
WHERE e.salary > m.salary;
""", "q03_earns_more_than_manager.sql", lang="sql")}
{C(r"""
(0 rows affected)
-- No employee earns more than their manager in this seed dataset.
-- Try: UPDATE hr.employees SET salary = 2000000 WHERE employee_id = 7
-- then re-run: (1 row) Kiran Bhat  2000000  Rahul Desai  1400000
""", lang="text")}

<h4>Q4. The 3 highest-paid employees in each department (top-N per group — preview of window functions)</h4>
{C(r"""
-- Without window functions (Week 12): a correlated subquery
SELECT e.first_name + N' ' + e.last_name AS employee,
       d.department_name,
       e.salary
FROM hr.employees AS e
JOIN hr.departments AS d ON d.department_id = e.department_id
WHERE (
    SELECT COUNT(*)
    FROM hr.employees AS e2
    WHERE e2.department_id = e.department_id
      AND e2.salary > e.salary
) < 3                       -- fewer than 3 people earn more → I'm in the top 3
ORDER BY d.department_name, e.salary DESC;
""", "q04_top3_per_dept.sql", lang="sql")}
{C(r"""
-- Returns top 3 per department (up to 21 rows; ties share rank).
-- Note: once you learn DENSE_RANK() OVER (PARTITION BY ...) next week,
-- this becomes two lines instead of a correlated subquery.
""", lang="text")}

<h4>Q5. Employees hired in the last 3 years, with years of service</h4>
{C(r"""
SELECT e.first_name + N' ' + e.last_name AS employee,
       e.hire_date,
       DATEDIFF(YEAR, e.hire_date, CAST(SYSDATETIME() AS DATE)) AS years_of_service,
       j.job_title
FROM hr.employees AS e
JOIN hr.jobs AS j ON j.job_id = e.job_id
WHERE e.hire_date >= DATEADD(YEAR, -3, CAST(SYSDATETIME() AS DATE))
ORDER BY e.hire_date DESC;
""", "q05_recent_hires.sql", lang="sql")}
{C(r"""
-- As of 2026-11-14, hires from 2023-11-14 onward:
employee         hire_date   years_of_service  job_title
---------------- ----------- ----------------  --------------------------
Chetan Kulkarni  2022-11-01  4                 Junior Software Engineer
Tanvi Ghosh      2023-02-15  3                 Junior Software Engineer
(exact rows depend on current date; adjust seed dates as needed)
""", lang="text")}

<h4>Q6. Departments with average salary above the company-wide average</h4>
{C(r"""
SELECT d.department_name,
       CAST(AVG(e.salary) AS DECIMAL(12,2)) AS dept_avg_salary,
       CAST((SELECT AVG(salary) FROM hr.employees) AS DECIMAL(12,2)) AS company_avg
FROM hr.employees AS e
JOIN hr.departments AS d ON d.department_id = e.department_id
GROUP BY d.department_name
HAVING AVG(e.salary) > (SELECT AVG(salary) FROM hr.employees)
ORDER BY dept_avg_salary DESC;
""", "q06_above_avg_depts.sql", lang="sql")}
{C(r"""
department_name     dept_avg_salary  company_avg
-------------------  ---------------  -----------
Engineering          1303222.22       ~937000
Product Management   ~1293000         ~937000
Finance              ~1143000         ~937000
(3 rows; exact figures depend on seed salaries after appraisal)
""", lang="text")}

<h4>Q7. Full manager chain for a given employee (using a CTE — preview)</h4>
{C(r"""
-- Recursive CTE: Week 12 topic; shown here for curiosity.
-- Walk up the management chain from Nikhil Verma (emp 13) to the CEO.
WITH ManagerChain AS
(
    SELECT employee_id, first_name, last_name, manager_id, 0 AS level
    FROM hr.employees
    WHERE employee_id = 13                          -- anchor: Nikhil Verma

    UNION ALL

    SELECT e.employee_id, e.first_name, e.last_name, e.manager_id, mc.level + 1
    FROM hr.employees AS e
    JOIN ManagerChain AS mc ON mc.manager_id = e.employee_id   -- walk up
)
SELECT level, first_name + N' ' + last_name AS name FROM ManagerChain ORDER BY level;
""", "q07_manager_chain.sql", lang="sql")}
{C(r"""
level  name
-----  ---------------
0      Nikhil Verma         (the employee)
1      Sneha Joshi          (direct manager)
2      Rahul Desai
3      Meera Krishnan
4      Priya Sharma
5      Vikram Nair          (CEO)
(6 rows)
""", lang="text")}

<h4>Q8. The most recent salary change for every employee</h4>
{C(r"""
SELECT e.first_name + N' ' + e.last_name AS employee,
       sh.change_date,
       sh.old_salary,
       sh.new_salary,
       sh.reason
FROM hr.employees AS e
JOIN hr.salary_history AS sh
    ON sh.employee_id = e.employee_id
   AND sh.change_date = (
        SELECT MAX(sh2.change_date)
        FROM hr.salary_history AS sh2
        WHERE sh2.employee_id = e.employee_id
   )
ORDER BY sh.change_date DESC, e.employee_id;
""", "q08_latest_salary_change.sql", lang="sql")}
{C(r"""
-- Employees who had a 2024 appraisal show change_date = 2024-04-01.
-- Others (managers, VPs) only have the initial hire row (their hire_date).
-- 30 rows total, one per employee.
""", lang="text")}

<h4>Q9. Employees with no direct reports (leaf nodes)</h4>
{C(r"""
SELECT e.employee_id,
       e.first_name + N' ' + e.last_name AS employee,
       j.job_title
FROM hr.employees AS e
JOIN hr.jobs AS j ON j.job_id = e.job_id
WHERE NOT EXISTS (
    SELECT 1 FROM hr.employees AS sub
    WHERE sub.manager_id = e.employee_id
)
ORDER BY j.job_title, e.last_name;
""", "q09_leaf_employees.sql", lang="sql")}
{C(r"""
-- Individual contributors: all JR engineers and analysts,
-- plus Sales Executives and HR Executives.
-- Expected: ~16-17 employees (those who manage nobody).
""", lang="text")}

<h4>Q10. Location-level payroll report (3-table join)</h4>
{C(r"""
SELECT l.city, l.state,
       COUNT(e.employee_id)              AS headcount,
       SUM(e.salary)                     AS total_payroll,
       CAST(MIN(e.salary) AS DECIMAL(12,2)) AS min_salary,
       CAST(MAX(e.salary) AS DECIMAL(12,2)) AS max_salary
FROM hr.locations AS l
JOIN hr.departments AS d ON d.location_id = l.location_id
JOIN hr.employees   AS e ON e.department_id = d.department_id
GROUP BY l.city, l.state
ORDER BY total_payroll DESC;
""", "q10_location_payroll.sql", lang="sql")}
{C(r"""
city        state          headcount  total_payroll  min_salary   max_salary
----------  -------------- ---------  -------------  -----------  -----------
Bengaluru   Karnataka      12         ~15000000      460000       3200000
Mumbai      Maharashtra    7          ~5000000       420000       1200000
Delhi       Delhi          4          ~2400000       400000       1100000
Pune        Maharashtra    4          ~2200000       528000       1350000
Hyderabad   Telangana      3          ~2200000       490000       900000
(5 rows; exact totals depend on post-appraisal salaries)
""", lang="text")}

<h3>Organise scripts in a git repository</h3>
{C(r"""
mkdir hr-schema && cd hr-schema
git init
# Move or copy your .sql files:
# 01_hr_setup.sql  02_locations.sql  03_jobs.sql  04_departments.sql
# 05_employees_ddl.sql  06_employees_seed.sql  07_dept_manager_fk.sql
# 08_salary_history.sql
# queries/q01_engineering_by_salary.sql ... q10_location_payroll.sql

git add .
git commit -m "Week 11: HR schema and seed data"

# Push to GitHub (create the repo first at github.com/nayak22)
git remote add origin https://github.com/nayak22/hr-schema.git
git branch -M main
git push -u origin main
""", "git_setup.sh", lang="bash")}

<h3>Week 11 revision checklist</h3>
{table(["Topic","Can you...","Status"],[
["SQL Server setup","Run the Docker command from memory and fix a weak-SA-password failure","☐"],
["Data types","Choose INT/BIGINT/DECIMAL/NVARCHAR/DATE/DATETIME2/BIT for a given column","☐"],
["NULL semantics","Explain 3-valued logic and name 3 traps","☐"],
["IDENTITY vs SEQUENCE","Say when you'd use each","☐"],
["Constraints","Write PK, FK ON DELETE CASCADE, UNIQUE, CHECK, DEFAULT with named constraints","☐"],
["Normalization","Walk from a flat table to 3NF and spot partial/transitive dependencies","☐"],
["SELECT fundamentals","Write queries with WHERE, LIKE, IN, BETWEEN, IS NULL, TOP, OFFSET-FETCH","☐"],
["Logical query order","Recite the 8-step order and explain the alias-in-WHERE error","☐"],
["INSERT / UPDATE / DELETE","Use OUTPUT, UPDATE FROM, the difference between DELETE and TRUNCATE","☐"],
["MERGE","Write a MERGE with HOLDLOCK and state its two main caveats","☐"],
["JOINs","Write all 5 types, a self join and NOT EXISTS anti-join without notes","☐"],
["HR schema","Explain the 5-table structure and all FK relationships","☐"]])}

<h3>Five-question quiz — predict the output or spot the bug</h3>
<details><summary>Q1. What does this return?</summary>
{C(r"""
SELECT department_name
FROM hr.departments
WHERE manager_id NOT IN (SELECT manager_id FROM hr.employees);
""", lang="sql")}
<b>Zero rows.</b> <code>hr.employees.manager_id</code> can be NULL (Vikram Nair). One NULL in the subquery list makes NOT IN return UNKNOWN for every row — the classic NULL trap. Fix with NOT EXISTS.</details>

<details><summary>Q2. How many rows does this return, and why might it surprise you?</summary>
{C(r"""
SELECT e.first_name, d.department_name
FROM hr.employees AS e
LEFT JOIN hr.departments AS d ON d.department_id = e.department_id
WHERE d.location_id = 1003;
""", lang="sql")}
<b>12 rows</b> (employees in Bengaluru departments — Engineering and Product Management). The WHERE filters the right side of the LEFT JOIN, dropping employees with NULL department_id (and all other locations). The LEFT JOIN effectively becomes an INNER JOIN. To keep employees without a department, move the location filter into ON.</details>

<details><summary>Q3. This INSERT fails. Why, and how do you fix it?</summary>
{C(r"""
INSERT INTO hr.employees
    (employee_id, first_name, last_name, email, hire_date, job_id, salary, department_id, manager_id)
VALUES (31, N'New', N'Hire', 'new.hire@company.in', '2026-11-15', 'ENG_JR', 350000, 10, 5);
""", lang="sql")}
<b>It fails the CHECK constraint on hr.employees.salary: 350000 is below the ENG_JR min_salary of 400000… wait — the CHECK is on <code>hr.jobs.min_salary/max_salary</code>, not on <code>hr.employees.salary</code>.</b> So actually this INSERT succeeds with the current schema — the salary band is advisory data, not enforced at insert time. This is the gap the stretch goal asks you to close (add a CHECK constraint or trigger comparing salary to the job band).</details>

<details><summary>Q4. What does the correlated subquery in Q4 (top-3 per department) return for a department with 10 people, all on different salaries?</summary>
<b>Exactly 3 rows</b> — those where fewer than 3 people have a higher salary. For the top earner: 0 people earn more (0 &lt; 3 ✓). Second: 1 person (1 &lt; 3 ✓). Third: 2 (2 &lt; 3 ✓). Fourth: 3 (3 &lt; 3 is FALSE). It generalises to any top-N by changing the constant. With ties (two people on the same salary), both are included — the same behaviour as DENSE_RANK.</details>

<details><summary>Q5. The salary_history table has a row with old_salary = 0.01 for every employee. Is this bad data or intentional design?</summary>
<b>Intentional</b> — it's the "initial hire" anchor row. Using 0 would fail <code>CK_salary_history_amounts CHECK (old_salary > 0)</code>, so 0.01 (one paise) is a sentinel meaning "no previous salary". A cleaner design would add a nullable <code>change_type</code> column (<code>'HIRE'</code>, <code>'APPRAISAL'</code>, <code>'CORRECTION'</code>) and allow old_salary = 0 for HIRE rows with a conditional CHECK, or simply leave old_salary NULL on initial inserts. Both are valid discussion points in a schema review.</details>

<div class="note tip"><b>Next week:</b> Advanced T-SQL — GROUP BY, HAVING, aggregate functions, window functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, running totals), CTEs, recursive CTEs, subqueries and derived tables. All queries will run against the HR schema you built this week.</div>
''',
iqs=[
("Basic","What does DATEDIFF(YEAR, hire_date, GETDATE()) measure?","The number of year boundaries crossed between the two dates — e.g. hire_date 2020-12-31 and today 2021-01-01 gives 1, even though only one day passed. For exact tenure in years use DATEDIFF(DAY, ...) / 365.25 or DATEDIFF(MONTH, ...) / 12. The choice depends on whether the business wants 'calendar years crossed' or 'actual time elapsed'."),
("Basic","What is the purpose of the seed data in a development schema?","It gives the schema a realistic dataset so queries can be written, tested and reasoned about immediately without application code. Good seed data covers all relevant cases: nulls, boundary values, all join paths, and enough volume to tell if aggregate results look plausible."),
("Intermediate","The correlated subquery in Q4 runs once per row in the outer query. What is its time complexity and how would you replace it in production?","O(n²) in the worst case — for every employee, a scan of their department. On large tables this is slow. The production replacement is a window function: DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) in a CTE, then filter WHERE rnk <= 3. Window functions are computed in a single pass over the data."),
("Intermediate","How would you back up and restore the HR schema to a different server?","At the database level: BACKUP DATABASE CompanyDb TO DISK = '/path/CompanyDb.bak' WITH COMPRESSION; then RESTORE DATABASE … WITH MOVE to adjust file paths. For just the schema and seed data: generate scripts in SSMS (right-click database → Tasks → Generate Scripts, include data). For CI/CD, keep numbered .sql files in git and replay them in order against a fresh database — the same approach used in this week's git setup.")])

# ================= BUILD =================
days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","SQL Server 2022 Setup and Data Types","Setup · Data types","Docker install, connections, databases, schemas, NULLs, IDENTITY vs SEQUENCE.","2 hrs"),
 (2,"TUE","Keys, Constraints and Normalization","Constraints · 3NF","PK/FK/UNIQUE/CHECK/DEFAULT, ER diagrams, 1NF→3NF walkthrough.","2 hrs"),
 (3,"WED","SELECT: Filtering, NULLs and Paging","SELECT · WHERE · Paging","WHERE, LIKE, IN, BETWEEN, IS NULL, ORDER BY, TOP, OFFSET-FETCH, DISTINCT.","2 hrs"),
 (4,"THU","INSERT, UPDATE, DELETE and MERGE","DML","Multi-row INSERT, OUTPUT clause, UPDATE FROM, DELETE vs TRUNCATE, MERGE.","2 hrs"),
 (5,"FRI","JOINs: All Five Types and Anti-joins","JOINs","INNER/LEFT/RIGHT/FULL/CROSS, self join, ON vs WHERE, NOT EXISTS vs NOT IN.","2 hrs"),
 (6,"SAT","HR Schema: Departments, Employees and Salary History","HR schema","Full CREATE TABLE scripts, 30-row seed, manager self-reference, audit table.","4 hrs"),
 (7,"SUN","10 Practice Queries, Git Setup and Revision","Practice &amp; Revision","10 HR queries with solutions, git repo, checklist, quiz, next-week preview.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week11.html", 11,
      "Week 11 — SQL Server 2022 Foundations", "Phase 2", "~18 hrs",
      ["Phase 2 · Week 11 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "HR schema"],
      "Phase 2 begins with the database layer. This week you install SQL Server 2022 Developer in Docker, master the essential data types, keys and constraints, write SELECT queries with filtering and paging, change data with INSERT/UPDATE/DELETE/MERGE, combine tables with all five join types, and finish Saturday by building the HR schema that every remaining SQL week will query.",
      cards, days)
print("built")
