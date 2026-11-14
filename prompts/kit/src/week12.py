import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# HR schema reference (introduced Week 11, used throughout Week 12)
# hr.locations   (location_id, city, state, country)
# hr.departments (department_id, department_name, manager_id FK→employees, location_id FK→locations)
# hr.jobs        (job_id, job_title, min_salary, max_salary)
# hr.employees   (employee_id, first_name, last_name, email, hire_date, job_id FK→jobs,
#                 salary, manager_id FK→employees, department_id FK→departments)
# hr.salary_history (history_id, employee_id FK→employees, old_salary, new_salary,
#                    change_date, changed_by)

# ================= DAY 1 =================
d1 = day(1, "MON", "GROUP BY, HAVING and aggregates",
"Master multi-column grouping, choose the right aggregate, understand WHERE vs HAVING, and get a first look at GROUPING SETS and ROLLUP.",
[("Aggregate function","Collapses many rows to one value per group: SUM, AVG, MIN, MAX, COUNT."),
("GROUP BY","Splits the result into groups and runs one aggregate per group."),
("COUNT(*)","Counts all rows in the group, including NULLs."),
("COUNT(col)","Counts non-NULL values in that column."),
("COUNT(DISTINCT col)","Counts distinct non-NULL values — deduplicated count."),
("SUM / AVG / MIN / MAX","Ignore NULLs automatically. SUM of an all-NULL column returns NULL."),
("HAVING","Filters groups <i>after</i> aggregation, the way WHERE filters rows before. Can reference aggregate results."),
("Multi-column GROUP BY","Groups on the unique combination of several columns."),
("GROUPING SETS","(SQL:1999) Lets one SELECT compute several grouping combinations at once; not covered in depth until DW week."),
("ROLLUP","Shorthand for a hierarchy of GROUPING SETS from most detailed to grand total."),
("Logical query order","FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY; SELECT aliases are not visible in HAVING."),
("NULL in grouping","All NULLs form their own group — they don't match, they collect.")],
["WHERE filters rows, HAVING filters groups — the difference is important for performance because WHERE reduces the data before grouping.",
"Column aliases defined in SELECT cannot be used in HAVING or GROUP BY in SQL Server; repeat the expression or use a derived table.",
"Every non-aggregated column in SELECT must appear in GROUP BY.",
"COUNT(DISTINCT col) scans a full sort pass; on large tables it can be slow — an index helps.",
"AVG of integers truncates to an integer in SQL Server; CAST one side to DECIMAL(18,4) first.",
"ROLLUP is awareness-level here; detail is in a later data-warehouse week."],
f'''
<h3>1. Basic aggregates</h3>
{C(r"""
USE CompanyDb;
GO
-- How many employees per department?
SELECT   d.department_name,
         COUNT(*)                        AS total_employees,
         COUNT(e.manager_id)             AS has_a_manager,     -- NULLs not counted
         COUNT(DISTINCT e.job_id)        AS distinct_jobs,
         CAST(AVG(CAST(e.salary AS DECIMAL(14,4))) AS DECIMAL(10,2))
                                         AS avg_salary,
         MIN(e.salary)                   AS min_salary,
         MAX(e.salary)                   AS max_salary,
         SUM(e.salary)                   AS total_payroll
FROM     hr.employees    AS e
JOIN     hr.departments  AS d ON d.department_id = e.department_id
GROUP BY d.department_name
ORDER BY total_payroll DESC;
""", "01_basic_aggregates.sql", lang="sql")}
{C(r"""
department_name  total_employees  has_a_manager  distinct_jobs  avg_salary  min_salary  max_salary  total_payroll
---------------  ---------------  -------------  -------------  ----------  ----------  ----------  -------------
Engineering      12               11             4              95000.00    62000       180000      1140000
Sales             8                8             2              72500.00    55000       120000       580000
Finance           5                5             3              88000.00    70000       115000       440000
HR                4                3             2              68000.00    55000        85000       272000
(example output)
""", lang="text")}
{warn("AVG(e.salary) with salary as INT gives an integer average due to integer division. Always CAST to DECIMAL before AVG when you want paise precision.", "Gotcha")}

<h3>2. WHERE vs HAVING</h3>
{C(r"""
-- ❌ Syntactically wrong: WHERE can't see aggregates
-- SELECT department_id, COUNT(*) AS cnt
-- FROM hr.employees
-- WHERE COUNT(*) > 3
-- GROUP BY department_id;

-- ✓ HAVING filters groups, WHERE filters rows first (much cheaper)
SELECT   e.department_id,
         COUNT(*)   AS cnt
FROM     hr.employees AS e
WHERE    e.hire_date >= '2022-01-01'       -- filters rows BEFORE grouping
GROUP BY e.department_id
HAVING   COUNT(*) > 2;                     -- filters groups AFTER grouping
""", "02_where_vs_having.sql", lang="sql")}
{table(["","WHERE","HAVING"],[
["When it runs","Before GROUP BY (on individual rows)","After GROUP BY (on groups)"],
["Can reference aggregates?","No","Yes"],
["Performance","Better — fewer rows to aggregate","Worse if used to filter what WHERE could"],
["NULL handling","Filters out NULLs normally","Same"]])}
{tip("If a condition doesn't involve an aggregate, put it in WHERE. Only move a condition to HAVING when it references an aggregate (SUM, COUNT, AVG, etc.).")}

<h3>3. Multi-column GROUP BY</h3>
{C(r"""
-- Headcount and average salary by department AND job title
SELECT   d.department_name,
         j.job_title,
         COUNT(*)                                            AS headcount,
         CAST(AVG(CAST(e.salary AS DECIMAL(14,4))) AS DECIMAL(10,2))
                                                            AS avg_salary
FROM     hr.employees   AS e
JOIN     hr.departments AS d ON d.department_id = e.department_id
JOIN     hr.jobs        AS j ON j.job_id        = e.job_id
GROUP BY d.department_name, j.job_title
HAVING   COUNT(*) >= 2
ORDER BY d.department_name, avg_salary DESC;
""", "03_multi_group.sql", lang="sql")}
{C(r"""
department_name  job_title          headcount  avg_salary
---------------  -----------------  ---------  ----------
Engineering      Software Engineer  5          92000.00
Engineering      Senior Engineer    4         120000.00
Sales            Sales Executive    6          70000.00
(example output)
""", lang="text")}

<h3>4. COUNT(DISTINCT) — unique-value counts</h3>
{C(r"""
-- How many employees joined per year, and how many DISTINCT job titles existed that year?
SELECT   YEAR(hire_date)            AS hire_year,
         COUNT(*)                   AS new_hires,
         COUNT(DISTINCT job_id)     AS distinct_jobs_hired_into
FROM     hr.employees
GROUP BY YEAR(hire_date)
ORDER BY hire_year;
""", "04_count_distinct.sql", lang="sql")}
{C(r"""
hire_year  new_hires  distinct_jobs_hired_into
---------  ---------  ------------------------
2019       3          2
2020       7          4
2021       5          3
2022       8          5
2023       6          3
2024       4          2
(example output)
""", lang="text")}

<h3>5. ROLLUP and GROUPING SETS (awareness)</h3>
<p>ROLLUP adds subtotal and grand-total rows automatically. The GROUPING() function distinguishes a real NULL value from a "total" NULL produced by ROLLUP.</p>
{C(r"""
-- Payroll by department, with a grand total row (awareness only — detail in the DW week)
SELECT   COALESCE(d.department_name, 'ALL DEPARTMENTS') AS dept,
         COUNT(*)                AS headcount,
         SUM(e.salary)           AS total_payroll
FROM     hr.employees   AS e
JOIN     hr.departments AS d ON d.department_id = e.department_id
GROUP BY ROLLUP(d.department_name);
-- Last row: dept='ALL DEPARTMENTS', headcount=total, total_payroll=grand total
""", "05_rollup.sql", lang="sql")}
{C(r"""
dept              headcount  total_payroll
----------------  ---------  -------------
Engineering       12         1140000
Finance            5          440000
HR                 4          272000
Sales              8          580000
ALL DEPARTMENTS   29         2432000      ← ROLLUP grand total row
(example output)
""", lang="text")}
''',
["Putting a non-aggregated column in SELECT but not in GROUP BY — SQL Server error 8120.",
"Using a column alias from SELECT in HAVING (not allowed in SQL Server; repeat the expression).",
"Forgetting that AVG of INTs is integer division.",
"COUNT(*) vs COUNT(col) — the difference matters when that column has NULLs.",
"Using HAVING where WHERE would do — extra rows go through the aggregation engine unnecessarily."],
("40 min", ["Count employees per department and show only departments with average salary above ₹70,000, ordered by average salary descending.",
"Show each job title with its minimum and maximum salary from hr.employees (not from hr.jobs), and flag jobs where the max is more than 1.5× the min.",
"Use ROLLUP to produce a summary: hiring count per year, per department, and grand total. Use COALESCE to label the totals."]),
[("Why can't you use a SELECT alias in HAVING?","SQL Server evaluates HAVING before SELECT aliases are computed (logical query order: FROM → WHERE → GROUP BY → HAVING → SELECT). Repeat the expression or wrap the query in a CTE/derived table."),
("What does COUNT(*) count that COUNT(col) doesn't?","COUNT(*) counts every row including NULLs. COUNT(col) counts only non-NULL values in that column."),
("What is the logical query processing order?","FROM, then WHERE (filter rows), then GROUP BY (form groups), then HAVING (filter groups), then SELECT (compute output columns), then ORDER BY.")],
[("Basic","What is the difference between WHERE and HAVING?","WHERE filters individual rows before grouping; it cannot reference aggregates. HAVING filters groups after GROUP BY; it can reference aggregates. Putting a non-aggregate condition in HAVING instead of WHERE forces SQL Server to aggregate more rows unnecessarily."),
("Basic","What does COUNT(DISTINCT col) return?","The number of distinct non-NULL values in that column within each group. It's useful for questions like 'how many different products were ordered per customer'. It costs more than COUNT(*) because it requires a sort or hash to deduplicate."),
("Basic","Every non-aggregated column in SELECT must appear in GROUP BY — why?","Because one group contains many rows with potentially different values for that column; without grouping it, there's no single value to show. SQL Server enforces this with error 8120."),
("Intermediate","A query returns NULL rows from GROUP BY you didn't expect. What could cause it?","Two common reasons: (1) the grouping column contains actual NULL values — SQL Server groups them together; (2) an outer join produced NULL-padded rows on the outer side that you're now grouping. Add IS NULL checks in WHERE, or use INNER JOIN."),
("Intermediate","How would you calculate the percentage of total salary each department represents?","Either a window function (SUM(salary) OVER ()) in a derived table, or a subquery in HAVING/SELECT: <code>SUM(salary) * 100.0 / (SELECT SUM(salary) FROM hr.employees)</code>."),
("Intermediate","What is ROLLUP and when would you use it?","ROLLUP is shorthand for a hierarchy of GROUPING SETS that adds subtotals and a grand total. It's most common in reporting and dashboards: GROUP BY ROLLUP(dept, team) produces one group per dept+team, one per dept (summing teams), and one overall total. Full detail in the data-warehouse week.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Subqueries",
"Write scalar, column, table, and correlated subqueries; understand when EXISTS wins over IN; and know the derived table pattern.",
[("Subquery","A SELECT nested inside another SQL statement, enclosed in parentheses."),
("Scalar subquery","Returns exactly one row and one column; used wherever a single value is expected (SELECT list, WHERE, HAVING)."),
("Column subquery","Returns one column but potentially many rows; used with IN / NOT IN / ANY / ALL."),
("Table subquery (derived table)","Returns a full table result; appears in FROM and must be aliased. Called an <i>inline view</i> in some databases."),
("Correlated subquery","References a column from the outer query. Re-executes once per outer row (usually replaced by EXISTS or a join)."),
("EXISTS","Returns TRUE if the subquery produces at least one row. Short-circuits after the first match."),
("NOT EXISTS","Anti-join: TRUE when the subquery returns no rows. NULL-safe — preferred over NOT IN."),
("IN / NOT IN","IN is equivalent to = ANY; NOT IN has the NULL trap — one NULL in the list makes NOT IN return nothing."),
("ANY / ALL","Rarely needed: = ANY is IN, > ALL means greater than the max, < ALL means less than the min."),
("Semi-join","Filters rows using a match in another table but adds no columns from it — cleanest with EXISTS."),
("Anti-join","Filters to rows that have no match — cleanest with NOT EXISTS."),
("Inline view","Another name for a derived table: a subquery in FROM.")],
["Scalar subqueries must return at most one row or SQL Server raises an error at runtime.",
"Correlated subqueries are often slow on large tables — test whether a join or window function is faster.",
"Use EXISTS/NOT EXISTS instead of IN/NOT IN when the inner column is nullable.",
"A derived table (subquery in FROM) can reference its own aggregates in WHERE — unlike the outer SELECT.",
"Name all derived table aliases clearly: 'dept_avg', 'top_earners', not 'x', 'y'."],
f'''
<h3>1. Scalar subquery</h3>
{C(r"""
-- Employees earning more than the company-wide average salary
SELECT  e.employee_id,
        e.first_name + ' ' + e.last_name  AS employee_name,
        e.salary,
        (SELECT AVG(CAST(salary AS DECIMAL(14,4))) FROM hr.employees)  AS company_avg
FROM    hr.employees AS e
WHERE   e.salary > (SELECT AVG(salary) FROM hr.employees);
""", "01_scalar_subquery.sql", lang="sql")}
{C(r"""
employee_id  employee_name     salary    company_avg
-----------  ----------------  --------  -----------
3            Asha Joshi         180000    88000.00
7            Vikram Nair        145000    88000.00
...
(example output)
""", lang="text")}
{tip("When the same scalar subquery is referenced more than once in a query, extract it into a CTE (tomorrow) or a derived table so it only runs once.")}

<h3>2. Column subquery and IN</h3>
{C(r"""
-- Employees in departments located in Maharashtra
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        e.department_id
FROM    hr.employees AS e
WHERE   e.department_id IN
        (
            SELECT  d.department_id
            FROM    hr.departments AS d
            JOIN    hr.locations   AS l ON l.location_id = d.location_id
            WHERE   l.state = N'Maharashtra'
        );
""", "02_in_subquery.sql", lang="sql")}

<h3>3. NOT IN — the NULL trap</h3>
{C(r"""
-- Managers (employees who manage at least one person)
-- ❌ NULL trap: if any employee has manager_id NULL, NOT IN returns zero rows
SELECT employee_id, first_name + ' ' + last_name AS name
FROM   hr.employees
WHERE  employee_id NOT IN (SELECT manager_id FROM hr.employees);  -- manager_id can be NULL!

-- ✓ NOT EXISTS is always NULL-safe
SELECT employee_id, first_name + ' ' + last_name AS name
FROM   hr.employees AS e
WHERE  NOT EXISTS
       (SELECT 1 FROM hr.employees AS m WHERE m.manager_id = e.employee_id);
""", "03_not_in_trap.sql", lang="sql")}
{warn("If the column in the IN subquery can be NULL, NOT IN may silently return zero rows because NULL &lt;&gt; x is UNKNOWN, not FALSE. Use NOT EXISTS or add WHERE col IS NOT NULL to the inner SELECT.", "Gotcha")}

<h3>4. EXISTS and NOT EXISTS</h3>
{C(r"""
-- Departments that have at least one employee (EXISTS = semi-join)
SELECT d.department_id, d.department_name
FROM   hr.departments AS d
WHERE  EXISTS
       (SELECT 1 FROM hr.employees AS e WHERE e.department_id = d.department_id);

-- Departments with no employees (NOT EXISTS = anti-join)
SELECT d.department_id, d.department_name
FROM   hr.departments AS d
WHERE  NOT EXISTS
       (SELECT 1 FROM hr.employees AS e WHERE e.department_id = d.department_id);
""", "04_exists.sql", lang="sql")}
<p>The inner SELECT of an EXISTS only needs to return at least one row. Convention is <code>SELECT 1</code> to make intent clear; <code>SELECT *</code> works too but looks like you care about the data.</p>

<h3>5. Correlated subquery</h3>
{C(r"""
-- Employees earning more than their department's average
SELECT  e.employee_id,
        e.first_name + ' ' + e.last_name  AS employee_name,
        e.salary                           AS salary,
        dept_avg.avg_sal                   AS dept_avg_salary
FROM    hr.employees AS e
JOIN    (
            SELECT  department_id,
                    AVG(CAST(salary AS DECIMAL(14,4)))  AS avg_sal
            FROM    hr.employees
            GROUP BY department_id
        ) AS dept_avg ON dept_avg.department_id = e.department_id
WHERE   e.salary > dept_avg.avg_sal
ORDER BY e.department_id, e.salary DESC;
-- Note: rewritten as a join to derived table, which is faster than a correlated subquery
-- (the correlated version re-runs the subquery for every outer row)
""", "05_correlated_to_join.sql", lang="sql")}
{C(r"""
-- ❌ Slow correlated version (re-executes per row):
SELECT  e.first_name + ' ' + e.last_name AS employee_name,
        e.salary
FROM    hr.employees AS e
WHERE   e.salary > (SELECT AVG(CAST(salary AS DECIMAL(14,4)))
                    FROM   hr.employees AS inner_e
                    WHERE  inner_e.department_id = e.department_id);  -- references outer e
""", lang="sql")}

<h3>6. Derived tables (table subquery in FROM)</h3>
{C(r"""
-- Top 3 earners per department using a derived table (window functions tomorrow are cleaner)
SELECT  ranked.department_name,
        ranked.employee_name,
        ranked.salary
FROM    (
            SELECT  d.department_name,
                    e.first_name + ' ' + e.last_name  AS employee_name,
                    e.salary,
                    ROW_NUMBER() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)
                        AS rn
            FROM    hr.employees   AS e
            JOIN    hr.departments AS d ON d.department_id = e.department_id
        ) AS ranked
WHERE   ranked.rn <= 3
ORDER BY ranked.department_name, ranked.salary DESC;
""", "06_derived_table.sql", lang="sql")}
{tip("Derived tables can reference their own aliases in WHERE but cannot be referenced more than once in the query. When you need to reference the same derived result twice, use a CTE (tomorrow).")}
''',
["Scalar subquery returning more than one row — runtime error 512. Add TOP(1) or ensure uniqueness.",
"NOT IN over a nullable column — the classic NULL trap.",
"Correlated subqueries on millions of rows — test with execution plans; often replaceable by a window function or derived table join.",
"Forgetting to alias a derived table — SQL Server error: every derived table must have an alias.",
"Nesting more than two or three subquery levels — CTEs will make the same logic readable."],
("40 min", ["Write a query showing departments whose total payroll exceeds the average departmental payroll (use a scalar subquery or derived table in HAVING).",
"List employees who have never had a salary change (NOT EXISTS against hr.salary_history).",
"Rewrite the correlated subquery in section 5 as a derived table join and check both give identical results."]),
[("Scalar vs column vs table subquery?","Scalar returns one value (one row, one column); used where a value is expected. Column returns one column, many rows; used with IN/ANY/ALL. Table returns rows and columns; used in FROM as a derived table."),
("EXISTS vs IN for performance?","EXISTS short-circuits after finding the first match and doesn't pull all values into memory. IN evaluates the whole subquery and builds a list. For large sets EXISTS is often faster, especially when the inner column is nullable."),
("Why alias a derived table?","SQL Server requires every table in FROM to have a name (alias or its own name). A subquery has no name of its own, so an alias is mandatory: <code>(...) AS alias_name</code>.")],
[("Basic","What is a correlated subquery?","A subquery that references a column from the outer query. It re-executes once per row of the outer query, making it logically like a function called per row. This is powerful but slow at scale — a join or window function is usually faster."),
("Basic","When would you choose EXISTS over IN?","When the inner column may contain NULLs (NOT IN's NULL trap), when you only need to check existence (not use the value), and when the subquery returns many rows (EXISTS short-circuits). Use IN when the list is small, static and NULL-free."),
("Basic","What is a derived table?","A subquery in the FROM clause, enclosed in parentheses and given an alias. It acts as a temporary named result set for that query only — not persisted like a view or temp table."),
("Intermediate","How do you rewrite a correlated subquery to avoid per-row re-execution?","Promote the inner query to a derived table or CTE grouped on the correlated column, then JOIN the outer query to that derived result once. The optimiser can then choose a hash join or merge join rather than a nested loop per row."),
("Intermediate","What does ANY / ALL do?","ANY (synonym: SOME) makes a comparison true if it's true for at least one value; ALL requires it to be true for every value. <code>salary > ALL (SELECT …)</code> means salary is greater than every value returned — equivalent to salary > MAX. These are rarely written directly; using MAX/MIN with a plain comparison is more readable."),
("Intermediate","Can a subquery appear in the SELECT clause?","Yes, as a scalar subquery — it must return at most one row and one column, and it's re-evaluated for every output row (similar to a correlated subquery). If the same value is needed in many columns, compute it once in a CTE or derived table.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Common Table Expressions (CTEs)",
"Write chained CTEs for readability, recursive CTEs for org charts, and understand when to use a CTE vs temp table vs derived table.",
[("CTE (Common Table Expression)","A named temporary result set defined with WITH and usable in the query that follows. Scoped to that single statement."),
("Non-recursive CTE","A simple named derived table; can be chained (multiple CTEs in one WITH)."),
("Recursive CTE","A CTE that references itself via UNION ALL, used for hierarchical or graph traversals."),
("Anchor member","The base case of a recursive CTE — the rows that start the traversal."),
("Recursive member","The part that JOINs the CTE to itself to find the next level."),
("MAXRECURSION","Query hint controlling the recursion depth limit; default 100. <code>OPTION (MAXRECURSION 0)</code> removes the limit."),
("WITH TIES","Used with TOP to include rows that tie for the last position (requires ORDER BY)."),
("Chained CTEs","Multiple CTEs in one WITH clause, each building on those defined before it."),
("Hierarchy","A parent-child tree structure: employees and their managers, categories and subcategories."),
("Level / depth","Computed column in a recursive CTE tracking how deep in the tree the current row is."),
("Path","A string column accumulating the route from root to current node, useful for cycle detection."),
("Cycle detection","Ensuring a recursive CTE doesn't loop forever on a graph with cycles (SQL Server's default MAXRECURSION 100 stops it after 100 levels).")],
["CTEs do not create any physical object — they're scoped to the single statement they precede.",
"You can reference a CTE more than once in the query that follows (unlike a derived table).",
"The anchor and recursive members must have the same number of columns with compatible types.",
"UNION ALL is required in recursive CTEs; UNION would deduplicate and is disallowed.",
"Keep recursion depth reasonable in production; a cycle in the data can hit MAXRECURSION 100.",
"CTEs do not auto-materialise — SQL Server may evaluate them multiple times; use a temp table if the same data is needed repeatedly in a large batch."],
f'''
<h3>1. Single CTE for readability</h3>
{C(r"""
-- Departments where average salary exceeds the company-wide average
WITH dept_averages AS (
    SELECT  department_id,
            AVG(CAST(salary AS DECIMAL(14,4))) AS avg_sal
    FROM    hr.employees
    GROUP BY department_id
),
company_avg AS (
    SELECT AVG(CAST(salary AS DECIMAL(14,4))) AS overall_avg
    FROM   hr.employees
)
SELECT  d.department_name,
        da.avg_sal               AS dept_avg,
        ca.overall_avg           AS company_avg,
        da.avg_sal - ca.overall_avg AS difference
FROM    hr.departments AS d
JOIN    dept_averages  AS da ON da.department_id = d.department_id
CROSS JOIN company_avg AS ca
WHERE  da.avg_sal > ca.overall_avg
ORDER BY da.avg_sal DESC;
""", "01_chained_cte.sql", lang="sql")}
{C(r"""
department_name  dept_avg    company_avg  difference
---------------  ----------  -----------  ----------
Engineering      95000.00    88000.00      7000.00
Finance          88800.00    88000.00       800.00
(example output)
""", lang="text")}
{tip("Chain CTEs in a single WITH clause separated by commas. Each CTE can reference CTEs defined earlier in the same WITH. The final SELECT (or INSERT/UPDATE/DELETE) uses all of them.")}

<h3>2. Recursive CTE — org chart</h3>
{C(r"""
-- Walk the management hierarchy from the top down, tracking level and path
WITH org_chart AS (
    -- Anchor: employees with no manager (top of the tree)
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name           AS employee_name,
            e.manager_id,
            e.salary,
            e.department_id,
            0                                          AS level,
            CAST(e.first_name + ' ' + e.last_name AS NVARCHAR(1000))
                                                       AS path
    FROM    hr.employees AS e
    WHERE   e.manager_id IS NULL              -- anchor: the CEO / top-level managers

    UNION ALL

    -- Recursive member: direct reports of the rows already in the CTE
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name           AS employee_name,
            e.manager_id,
            e.salary,
            e.department_id,
            oc.level + 1                               AS level,
            CAST(oc.path + ' > ' + e.first_name + ' ' + e.last_name AS NVARCHAR(1000))
                                                       AS path
    FROM    hr.employees AS e
    JOIN    org_chart    AS oc ON oc.employee_id = e.manager_id
)
SELECT  REPLICATE('    ', level) + employee_name  AS indented_name,
        level,
        path
FROM    org_chart
ORDER BY path;
""", "02_recursive_cte.sql", lang="sql")}
{C(r"""
indented_name                           level  path
--------------------------------------  -----  ----------------------------------------
Priya Sharma                            0      Priya Sharma
    Asha Joshi                          1      Priya Sharma > Asha Joshi
        Karan Mehta                     2      Priya Sharma > Asha Joshi > Karan Mehta
        Riya Desai                      2      Priya Sharma > Asha Joshi > Riya Desai
    Vikram Nair                         1      Priya Sharma > Vikram Nair
        Meena Pillai                    2      Priya Sharma > Vikram Nair > Meena Pillai
(example output)
""", lang="text")}
{warn("The default MAXRECURSION is 100. Add <code>OPTION (MAXRECURSION 200)</code> at the end of the statement for deeper trees, or <code>MAXRECURSION 0</code> to remove the limit entirely (risk on cyclic data). Data cycles (A manages B who manages A) are stopped only by MAXRECURSION — add a cycle-guard path check in production.", "Watch out")}

<h3>3. MAXRECURSION and cycle guard</h3>
{C(r"""
-- Query hint at the end of the whole statement (not inside the CTE):
WITH org_chart AS (
    -- ... same as above ...
    SELECT employee_id, first_name + ' ' + last_name AS nm, manager_id, 0 AS lvl,
           CAST(employee_id AS VARCHAR(500)) AS id_path
    FROM   hr.employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.first_name + ' ' + e.last_name, e.manager_id, oc.lvl + 1,
           CAST(oc.id_path + ',' + CAST(e.employee_id AS VARCHAR(10)) AS VARCHAR(500))
    FROM   hr.employees e
    JOIN   org_chart    oc ON oc.employee_id = e.manager_id
    WHERE  CHARINDEX(',' + CAST(e.employee_id AS VARCHAR(10)) + ',',
                     ',' + oc.id_path + ',') = 0  -- cycle guard: stop if already visited
)
SELECT indented = REPLICATE('  ', lvl) + nm, lvl FROM org_chart ORDER BY id_path
OPTION (MAXRECURSION 500);    -- hint at statement end
""", "03_maxrecursion.sql", lang="sql")}

<h3>4. CTE vs temp table vs derived table</h3>
{table(["","CTE","Derived table","Temp table (#t)"],[
["Scope","Single statement","Single query","Session or scope"],
["Reuse in same query","Yes (all CTEs)","No","Yes (many statements)"],
["Indexable","No","No","Yes (great for multi-step ETL)"],
["Automatic materialisation","No (may re-evaluate)","No","Yes (fully computed once)"],
["Readable for hierarchy/recursion","Excellent","Hard to read","Wordy"],
["Statistics available","No","No","Yes"],
["Recommended for","Readability, recursive queries","One-off ad-hoc sub-results","Multi-step logic, repeated use, large intermediate results"]])}
{C(r"""
-- Temp table version of the same CTE (use when the intermediate result is large
-- and referenced in several later queries in the same batch):
DROP TABLE IF EXISTS #dept_averages;
SELECT  department_id,
        AVG(CAST(salary AS DECIMAL(14,4))) AS avg_sal
INTO    #dept_averages
FROM    hr.employees
GROUP BY department_id;

-- Now any number of queries can join to #dept_averages:
SELECT d.department_name, da.avg_sal
FROM   hr.departments AS d
JOIN   #dept_averages AS da ON da.department_id = d.department_id;
""", "04_temp_table.sql", lang="sql")}
''',
["Using UNION instead of UNION ALL in the recursive member — SQL Server rejects it.",
"Referencing a CTE from a different statement — out of scope; use a view or temp table.",
"Not casting path/accumulated columns to sufficient length — results silently truncate.",
"Forgetting the MAXRECURSION hint on deep hierarchies (> 100 levels).",
"Believing CTEs materialise once — they don't; a temp table is needed if you need guaranteed single evaluation."],
("40 min", ["Write a chained CTE that first calculates each employee's latest salary change from hr.salary_history, then joins it back to hr.employees to show employees whose current salary differs from what hr.salary_history records (data quality check).",
"Write a recursive CTE that returns the full chain of managers for a given employee_id, stopping at the top. Add a level column.",
"Compare the query plan of a chained CTE vs the equivalent temp table approach and note which uses a clustered index scan vs a Clustered Index Seek."]),
[("What's the difference between a CTE and a temp table?","A CTE lives for one statement only and may be re-evaluated by the optimiser; it has no statistics or indexes. A temp table persists for the session, is physically created in tempdb, can be indexed and has statistics — better for large intermediate results referenced many times."),
("How do you stop a recursive CTE from looping?","Either by SQL Server's MAXRECURSION setting (default 100), or by adding a WHERE guard in the recursive member that checks the path string doesn't already contain the current row's ID. The MAXRECURSION hint is added at the end of the statement: OPTION (MAXRECURSION n)."),
("Can you INSERT/UPDATE/DELETE using a CTE?","Yes. Write a CTE that identifies the rows, then use an INSERT/UPDATE/DELETE after the closing parenthesis that references the CTE. This is common for batch updates with complex filtering.")],
[("Basic","What is a CTE and when would you use it instead of a subquery?","A CTE is a named temporary result defined with WITH before the main query. Use it instead of a nested subquery when: (1) the same derived result is referenced more than once; (2) a subquery would be deeply nested; (3) you need recursion. CTEs improve readability without changing the execution plan."),
("Basic","Explain the structure of a recursive CTE.","A recursive CTE has two parts joined by UNION ALL: the anchor member (the base case returning the starting rows) and the recursive member (a SELECT that JOINs the CTE to itself to find the next level). SQL Server executes the anchor once, then repeatedly executes the recursive member against the latest level's rows until it returns no more rows or hits MAXRECURSION."),
("Basic","What happens if MAXRECURSION is exceeded?","SQL Server raises error 530: 'The statement terminated. The maximum recursion 100 has been exhausted before statement completion.' You can raise the limit with OPTION (MAXRECURSION n) or remove it with OPTION (MAXRECURSION 0). The latter is risky on cyclic data."),
("Intermediate","Can a CTE be referenced more than once in the same query?","Yes — that's one advantage over derived tables. All CTEs in the WITH block are in scope for the main query and for each other (each can reference any CTE defined before it). However, SQL Server may still re-evaluate the CTE once per reference unless it chooses to spool; if single-evaluation is essential, use a temp table."),
("Intermediate","How would you delete duplicate rows using a CTE?","Assign row numbers with ROW_NUMBER() OVER (PARTITION BY key_cols ORDER BY ...) in a CTE, then DELETE FROM that CTE WHERE rn > 1. SQL Server allows DML against a CTE when the CTE references exactly one base table."),
("Intermediate","CTE vs view: what's different?","A CTE exists only for the duration of one statement; it cannot be reused by other queries or stored in the database. A view is a named persistent object others can query. Use a CTE for query-local clarity; use a view for a reusable, security-layer, or join shorthand needed across the codebase.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Window functions",
"Use ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG, LEAD, running totals and moving averages without collapsing your rows.",
[("Window function","A function applied over a 'window' of rows related to the current row. Unlike GROUP BY, it does not collapse rows."),
("OVER clause","Defines the window: PARTITION BY (grouping), ORDER BY (sorting within partition), and optional frame."),
("PARTITION BY","Resets the window calculation for each group, like GROUP BY but without collapsing rows."),
("ORDER BY (in OVER)","Determines the order within each partition for ranking and running calculations."),
("Frame clause","Specifies which rows of the partition are included in the calculation relative to the current row: ROWS BETWEEN / RANGE BETWEEN."),
("ROW_NUMBER()","Unique sequential number per row within the partition, based on ORDER BY."),
("RANK()","Same number for ties, then skips (1,1,3 for two ties at first)."),
("DENSE_RANK()","Same number for ties, no skip (1,1,2 for two ties at first)."),
("NTILE(n)","Divides rows into n equal buckets and assigns each row its bucket number."),
("LAG(col, n, default)","Value of col from n rows before the current row in the partition."),
("LEAD(col, n, default)","Value of col from n rows after the current row in the partition."),
("ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW","Classic running total frame."),
("RANGE vs ROWS","RANGE groups ties into the same frame boundary; ROWS is strict position. ROWS is almost always what you want.")],
["Window functions run after WHERE and GROUP BY but before SELECT expressions — they see aggregated rows.",
"You can use a window function in ORDER BY or in a derived table/CTE but not directly in WHERE or HAVING.",
"RANK leaves gaps; DENSE_RANK does not — pick based on how ties should read.",
"ROWS BETWEEN is strict (physical position); RANGE BETWEEN treats ties as a group (less predictable). Default when ORDER BY is specified: RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.",
"LAG/LEAD default to NULL when there's no preceding/following row — supply a default if needed.",
"NTILE distributes rows as evenly as possible; with uneven distribution the first buckets get one extra row."],
f'''
<h3>1. ROW_NUMBER, RANK, DENSE_RANK</h3>
{C(r"""
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        d.department_name,
        e.salary,
        ROW_NUMBER()  OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS row_num,
        RANK()        OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS rnk,
        DENSE_RANK()  OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS dense_rnk
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
ORDER BY d.department_name, e.salary DESC;
""", "01_ranking.sql", lang="sql")}
{C(r"""
employee_name     department_name  salary   row_num  rnk  dense_rnk
----------------  ---------------  -------  -------  ---  ---------
Asha Joshi        Engineering      180000   1        1    1
Vikram Nair       Engineering      145000   2        2    2
Karan Mehta       Engineering      145000   3        2    2       ← tie: RANK skips 3, DENSE_RANK doesn't
Priya Desai       Engineering      120000   4        4    3
...
(example output)
""", lang="text")}
{table(["Function","Ties","Gaps after tie","Use when"],[
["ROW_NUMBER()","Never","N/A","You need a truly unique number per row"],
["RANK()","Yes","Yes (1,1,3)","Olympic-style ranking, OK with gaps"],
["DENSE_RANK()","Yes","No (1,1,2)","Category leaderboards without gaps"]])}

<h3>2. NTILE</h3>
{C(r"""
-- Divide employees into 4 salary quartiles within each department
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        e.salary,
        d.department_name,
        NTILE(4) OVER (PARTITION BY e.department_id ORDER BY e.salary)  AS salary_quartile
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
ORDER BY d.department_name, e.salary;
""", "02_ntile.sql", lang="sql")}
{C(r"""
employee_name     salary   department_name  salary_quartile
----------------  -------  ---------------  ---------------
Rohit Verma       62000    Engineering      1
Anjali Singh      75000    Engineering      1
Deepak Rao        82000    Engineering      1
Nisha Kapoor      90000    Engineering      2
Sunil Sharma      95000    Engineering      2
...
(example output)
""", lang="text")}

<h3>3. LAG and LEAD — accessing neighbouring rows</h3>
{C(r"""
-- For each salary change in salary_history: show previous salary and % change
SELECT  sh.employee_id,
        e.first_name + ' ' + e.last_name  AS employee_name,
        sh.change_date,
        sh.new_salary,
        LAG(sh.new_salary, 1, sh.old_salary)
            OVER (PARTITION BY sh.employee_id ORDER BY sh.change_date)  AS prev_salary,
        CAST(
            (sh.new_salary - LAG(sh.new_salary, 1, sh.old_salary)
                OVER (PARTITION BY sh.employee_id ORDER BY sh.change_date))
            * 100.0 / NULLIF(LAG(sh.new_salary, 1, sh.old_salary)
                OVER (PARTITION BY sh.employee_id ORDER BY sh.change_date), 0)
        AS DECIMAL(6,2))  AS pct_change
FROM    hr.salary_history AS sh
JOIN    hr.employees      AS e ON e.employee_id = sh.employee_id
ORDER BY sh.employee_id, sh.change_date;
""", "03_lag_lead.sql", lang="sql")}
{C(r"""
employee_id  employee_name  change_date  new_salary  prev_salary  pct_change
-----------  -------------  -----------  ----------  -----------  ----------
3            Asha Joshi     2021-07-01   120000      95000        26.32
3            Asha Joshi     2023-01-15   145000      120000       20.83
3            Asha Joshi     2024-06-01   180000      145000       24.14
(example output)
""", lang="text")}

<h3>4. Running totals and moving averages</h3>
{C(r"""
-- Running payroll total by hire month, plus 3-month moving average
WITH monthly AS (
    SELECT  DATEFROMPARTS(YEAR(hire_date), MONTH(hire_date), 1)  AS hire_month,
            SUM(salary)                                           AS monthly_payroll
    FROM    hr.employees
    GROUP BY DATEFROMPARTS(YEAR(hire_date), MONTH(hire_date), 1)
)
SELECT  hire_month,
        monthly_payroll,
        SUM(monthly_payroll)
            OVER (ORDER BY hire_month
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)   AS running_total,
        AVG(CAST(monthly_payroll AS DECIMAL(14,4)))
            OVER (ORDER BY hire_month
                  ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)           AS moving_avg_3m
FROM    monthly
ORDER BY hire_month;
""", "04_running_total.sql", lang="sql")}
{C(r"""
hire_month   monthly_payroll  running_total  moving_avg_3m
-----------  ---------------  -------------  -------------
2019-06-01   125000           125000         125000.0000
2019-09-01    95000           220000         110000.0000
2020-01-01   280000           500000         166666.6667
2020-04-01   310000           810000         228333.3333
(example output)
""", lang="text")}
{warn("The default window frame when ORDER BY is specified inside OVER is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW (not ROWS). RANGE groups tied ORDER BY values into the same boundary — always specify ROWS BETWEEN explicitly for running totals and moving averages.", "Important")}

<h3>5. Top-N per group and de-duplication</h3>
{C(r"""
-- Top 3 earners per department (clean CTE + ROW_NUMBER pattern)
WITH ranked AS (
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name  AS employee_name,
            d.department_name,
            e.salary,
            ROW_NUMBER() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS rn
    FROM    hr.employees   AS e
    JOIN    hr.departments AS d ON d.department_id = e.department_id
)
SELECT department_name, employee_name, salary
FROM   ranked
WHERE  rn <= 3
ORDER BY department_name, salary DESC;

-- De-duplicate: keep only the latest salary_history row per employee
WITH dedupe AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY change_date DESC) AS rn
    FROM   hr.salary_history
)
DELETE FROM dedupe WHERE rn > 1;   -- DML on a CTE works when it maps to one base table
""", "05_topn_dedupe.sql", lang="sql")}
''',
["Using a window function in WHERE directly — not allowed; wrap in a CTE or derived table.",
"Not specifying ROWS BETWEEN — default RANGE BETWEEN may produce unexpected results when rows tie on ORDER BY.",
"Confusing RANK and DENSE_RANK on leaderboards (do you want gaps or not?).",
"LAG/LEAD returning NULL on first/last row — always supply a default if downstream code expects a value.",
"Over-using window functions in a single SELECT — complex nested OVER clauses make them hard to read; use a CTE to stage them."],
("40 min", ["Write a query that shows each employee's salary alongside their department's min, max and average salary using window functions — without GROUP BY or subqueries.",
"Use LAG to calculate the number of days between consecutive salary changes for each employee.",
"Find employees who are in the top-10% of earners company-wide using NTILE(10) and show their names, salaries and ntile bucket."]),
[("RANK vs DENSE_RANK on a 5-row result where rows 2 and 3 tie?","RANK: 1,2,2,4,5 (skips 3). DENSE_RANK: 1,2,2,3,4 (no skip). ROW_NUMBER would give 1,2,3,4,5 regardless of ties."),
("Why can't a window function appear in WHERE?","Window functions are computed after WHERE filters rows. If WHERE could reference a window function, the filter would need to run after the window, which is a logical cycle. Use a CTE or derived table to materialise the window result first."),
("ROWS BETWEEN vs RANGE BETWEEN?","ROWS BETWEEN counts physical rows. RANGE BETWEEN treats rows with equal ORDER BY values as a group at the same boundary. ROWS is predictable and almost always the right choice for running totals and moving averages.")],
[("Basic","What does PARTITION BY do in a window function?","It divides the result set into partitions (like GROUP BY) so the window function resets its calculation for each partition. Rows from other partitions are not visible to the calculation. Unlike GROUP BY it doesn't collapse rows — every row is still returned."),
("Basic","What is the difference between ROW_NUMBER, RANK and DENSE_RANK?","ROW_NUMBER gives a unique sequential number regardless of ties. RANK gives the same number to ties but then skips numbers (1,1,3). DENSE_RANK gives the same number to ties but doesn't skip (1,1,2). Choose based on whether you want gaps in the sequence after ties."),
("Basic","What are LAG and LEAD used for?","LAG accesses the value of a column from a previous row in the same partition (default: 1 row back). LEAD accesses a future row. Classic uses: calculating growth rates, finding gaps between events, comparing this row to the previous record."),
("Intermediate","How do you calculate a 7-day moving average?","Use AVG(...) OVER (ORDER BY date_col ROWS BETWEEN 6 PRECEDING AND CURRENT ROW). The ROWS BETWEEN clause includes the current row and the 6 that come before it in ORDER BY sequence, giving you a 7-row window."),
("Intermediate","How do you get the second-highest salary without a subquery?","Use DENSE_RANK() OVER (ORDER BY salary DESC) in a CTE, then filter WHERE dense_rnk = 2. This correctly handles ties — multiple employees may share second place."),
("Intermediate","Can you combine GROUP BY and window functions in one query?","Yes. Window functions run after GROUP BY, so they see aggregated rows. Example: GROUP BY department to get a sum, then use a window function over those grouped rows to compute each department's percentage of the grand total. The window function sits in the SELECT list of a grouped query.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Views, table-valued functions and APPLY",
"Create views with SCHEMABINDING, compare inline vs multi-statement TVFs, understand scalar function cost and when SQL Server can inline them, and use CROSS/OUTER APPLY.",
[("View","A named stored SELECT query. Used as a table in queries; does not store data (unless indexed)."),
("SCHEMABINDING","Prevents DROP or ALTER on any base object the view depends on. Required for indexed views."),
("Indexed view","A view with a unique clustered index physically materialising the result. Needs SCHEMABINDING and several restrictions."),
("Inline TVF (ITVF)","A table-valued function returning a single SELECT; equivalent to a parameterised view. Zero overhead — optimiser treats it as a macro."),
("Multi-statement TVF (MSTVF)","A TVF with BEGIN/END and multiple statements, populating a table variable and returning it. Costly — acts like a black box, row estimate always 1 (before SQL 2019)."),
("Scalar UDF","A function returning one value. Pre-SQL Server 2019 it blocks parallelism and re-executes per row. Post-2019, SQL Server may inline it."),
("Scalar UDF inlining","SQL Server 2019+ automatically converts eligible scalar UDFs to inline expressions, restoring performance."),
("CROSS APPLY","Like CROSS JOIN but the right side can be a function or subquery that uses a column from the left side. Returns only rows where the right side returns a result."),
("OUTER APPLY","Like LEFT JOIN equivalent of CROSS APPLY — also keeps left rows where the right side returns nothing (NULL-padded)."),
("TVF","Table-valued function: a function you can query in FROM."),
("Deterministic","A function that always returns the same result for the same inputs — required for use in computed columns and indexed views.")],
["SCHEMABINDING on a view prevents schema changes to its base tables without dropping the view first — a protection and a commitment.",
"Always prefer an ITVF over a scalar UDF when you need per-row calculation on a set of rows; the optimiser can reason about it.",
"MSTVF: think of it as a temp table returned — the row count estimate is usually wrong, leading to bad plans.",
"CROSS APPLY is the natural fit when calling a TVF once per row, or when a correlated derived table needs an alias.",
"OUTER APPLY preserves rows from the left side even when the right side returns nothing — mirrors LEFT JOIN.",
"Check sys.sql_modules or the Object Explorer for a view's definition; never rely on the view alone without verifying the base tables."],
f'''
<h3>1. Creating views with SCHEMABINDING</h3>
{C(r"""
-- A view that centralises the employee-department join (commonly queried)
CREATE OR ALTER VIEW hr.vw_employee_details
WITH SCHEMABINDING
AS
SELECT  e.employee_id,
        e.first_name,
        e.last_name,
        e.first_name + ' ' + e.last_name  AS full_name,
        e.salary,
        e.hire_date,
        d.department_name,
        j.job_title,
        l.city                             AS work_city,
        l.state                            AS work_state,
        m.first_name + ' ' + m.last_name   AS manager_name
FROM    hr.employees    AS e
JOIN    hr.departments  AS d ON d.department_id  = e.department_id
JOIN    hr.jobs         AS j ON j.job_id         = e.job_id
JOIN    hr.locations    AS l ON l.location_id    = d.location_id
LEFT JOIN hr.employees  AS m ON m.employee_id    = e.manager_id;
GO
-- Use it like a table:
SELECT full_name, department_name, salary, manager_name
FROM   hr.vw_employee_details
WHERE  work_state = N'Karnataka'
ORDER BY salary DESC;
""", "01_view.sql", lang="sql")}
{tip("WITH SCHEMABINDING requires two-part names (hr.employees not just employees). Try dropping or renaming a base table column after creating this view — SQL Server refuses. This is the safety net that makes refactoring safe.")}
{table(["Scenario","Use a view","Use a CTE instead"],[
["Same join reused across many queries","Yes","No (single-query scope)"],
["Need to grant SELECT to a report user without exposing base tables","Yes","No"],
["Logic needed inside one complex query","No","Yes"],
["Want indexed materialisation","Yes (indexed view)","No"],
["Parameterised result (varies per input)","No — use a TVF","Yes (CTE)"]])}

<h3>2. Inline TVF — parameterised view</h3>
{C(r"""
-- ITVF: returns employees hired in a given year with their department details
CREATE OR ALTER FUNCTION hr.fn_employees_hired_in_year (@year INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN
(
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name  AS full_name,
            e.hire_date,
            e.salary,
            d.department_name,
            j.job_title
    FROM    hr.employees    AS e
    JOIN    hr.departments  AS d ON d.department_id = e.department_id
            JOIN    hr.jobs AS j ON j.job_id        = e.job_id
    WHERE   YEAR(e.hire_date) = @year
);
GO
-- Call it:
SELECT * FROM hr.fn_employees_hired_in_year(2023) ORDER BY salary DESC;
""", "02_itvf.sql", lang="sql")}
{C(r"""
employee_id  full_name         hire_date   salary   department_name  job_title
-----------  ----------------  ----------  -------  ---------------  ------------------
7            Vikram Nair       2023-03-01  145000   Engineering      Senior Engineer
14           Anjali Singh      2023-07-15   75000   HR               HR Specialist
(example output)
""", lang="text")}
{warn("An ITVF body is a single RETURN (...) with a single SELECT — no variables, no IF/ELSE. The moment you need control flow or multiple statements, it becomes an MSTVF (or a CTE).", "Design rule")}

<h3>3. Multi-statement TVF and scalar UDF cost</h3>
{C(r"""
-- MSTVF (use sparingly — bad row estimates before SQL 2019)
CREATE OR ALTER FUNCTION hr.fn_dept_summary (@min_headcount INT)
RETURNS @result TABLE (
    department_name  NVARCHAR(100),
    headcount        INT,
    avg_salary       DECIMAL(10,2)
)
WITH SCHEMABINDING
AS
BEGIN
    INSERT INTO @result
    SELECT  d.department_name,
            COUNT(*)                                            AS headcount,
            AVG(CAST(e.salary AS DECIMAL(14,4)))               AS avg_salary
    FROM    hr.employees   AS e
    JOIN    hr.departments AS d ON d.department_id = e.department_id
    GROUP BY d.department_name
    HAVING  COUNT(*) >= @min_headcount;
    RETURN;
END;
GO
SELECT * FROM hr.fn_dept_summary(3) ORDER BY avg_salary DESC;
""", "03_mstvf.sql", lang="sql")}
{C(r"""
-- Scalar UDF (pre-SQL 2019 it runs per row and blocks parallelism):
CREATE OR ALTER FUNCTION hr.fn_salary_band (@salary DECIMAL(10,2))
RETURNS NVARCHAR(10)
WITH SCHEMABINDING
AS
BEGIN
    RETURN CASE
        WHEN @salary < 60000  THEN N'Band A'
        WHEN @salary < 90000  THEN N'Band B'
        WHEN @salary < 130000 THEN N'Band C'
        ELSE N'Band D'
    END;
END;
GO
-- SQL Server 2019+ may inline this automatically (check with:
-- SELECT is_inlineable FROM sys.sql_modules WHERE object_id = OBJECT_ID('hr.fn_salary_band'))
-- If not inlineable: replace with an inline CASE expression in the query instead.
SELECT full_name, salary, hr.fn_salary_band(salary) AS band
FROM   hr.vw_employee_details;
""", "04_scalar_udf.sql", lang="sql")}

<h3>4. CROSS APPLY and OUTER APPLY</h3>
{C(r"""
-- CROSS APPLY: for each department, call the TVF and get its top 2 earners
SELECT  d.department_name,
        top_earners.full_name,
        top_earners.salary
FROM    hr.departments AS d
CROSS APPLY
(
    SELECT TOP(2)
           e.first_name + ' ' + e.last_name  AS full_name,
           e.salary
    FROM   hr.employees AS e
    WHERE  e.department_id = d.department_id   -- references the outer table
    ORDER BY e.salary DESC
) AS top_earners
ORDER BY d.department_name, top_earners.salary DESC;
""", "05_cross_apply.sql", lang="sql")}
{C(r"""
department_name  full_name        salary
---------------  ---------------  -------
Engineering      Asha Joshi       180000
Engineering      Vikram Nair      145000
Finance          Pooja Iyer       115000
Finance          Rahul Gupta       98000
HR               Tara Reddy        85000
HR               Meena Pillai      72000
(example output)
""", lang="text")}
{C(r"""
-- OUTER APPLY: also keeps departments that have NO employees (NULL-padded)
SELECT  d.department_name,
        top_earners.full_name,
        top_earners.salary
FROM    hr.departments AS d
OUTER APPLY
(
    SELECT TOP(2)
           e.first_name + ' ' + e.last_name  AS full_name,
           e.salary
    FROM   hr.employees AS e
    WHERE  e.department_id = d.department_id
    ORDER BY e.salary DESC
) AS top_earners
ORDER BY d.department_name;
-- Departments with no employees appear with full_name = NULL, salary = NULL
""", "06_outer_apply.sql", lang="sql")}
{table(["","CROSS APPLY","OUTER APPLY"],[
["Rows kept when right side returns nothing","Dropped","Kept, right columns are NULL"],
["JOIN equivalent","INNER JOIN","LEFT JOIN"],
["Use when","You only care about matches","You need all left rows"]])}
''',
["Creating a view without SCHEMABINDING, then breaking it by altering a base table column.",
"Writing a scalar UDF that is called in a WHERE clause on millions of rows — force-disables parallelism on pre-2019 SQL Server.",
"Using an MSTVF where an ITVF would work — the row estimate of 1 leads to bad join strategies.",
"CROSS APPLY where OUTER APPLY was intended — silent loss of rows.",
"Forgetting the two-part schema-qualified names required by SCHEMABINDING."],
("40 min", ["Create <code>hr.vw_salary_bands</code> (a view with SCHEMABINDING) that shows each employee's name, salary, and band (< 60k = A, < 90k = B, < 130k = C, else D).",
"Write an ITVF <code>hr.fn_team(manager_id INT)</code> that returns all direct reports of a given manager.",
"Use CROSS APPLY with a subquery to show each department and the hire date of its most recently hired employee."]),
[("Why use SCHEMABINDING on a view?","It binds the view to the schema of its base objects, preventing DROP or ALTER of any column, table or function the view depends on. It is required for creating an indexed view, and it's good practice on any view you depend on — it makes refactoring explicit."),
("ITVF vs MSTVF: which performs better?","An ITVF is treated as an inline macro by the optimiser — it can push predicates into it, estimate cardinality from base table statistics, and use parallelism. An MSTVF is a black box; before SQL 2019 the row estimate was always 1 or 100 regardless of data, leading to bad plans. Prefer ITVF whenever possible."),
("What is scalar UDF inlining?","SQL Server 2019+ can automatically convert eligible scalar UDFs to equivalent inline expressions during compilation. An inlineable UDF behaves like an ITVF — the optimiser sees through it. Check <code>sys.sql_modules.is_inlineable</code>. A UDF is not inlineable if it has side effects, recursion, or references non-deterministic functions.")],
[("Basic","What is a view and why use one?","A view is a named, stored SELECT query treated as a virtual table. Use views to: centralise a commonly reused join, restrict column visibility for security (grant SELECT on the view, not the base table), simplify complex queries for end users, and enforce a consistent query structure."),
("Basic","What is the difference between CROSS APPLY and OUTER APPLY?","Both call a right-side expression once per left-side row. CROSS APPLY drops left rows where the right side returns no rows (like INNER JOIN). OUTER APPLY keeps them with NULLs on the right (like LEFT JOIN). The key capability: the right side can reference columns from the left, which a plain JOIN cannot."),
("Basic","What is a table-valued function?","A user-defined function that returns a table result instead of a scalar value. It can be used in FROM, JOINed to other tables, and filtered with WHERE. Inline TVFs (single RETURN SELECT) have no performance overhead; multi-statement TVFs (BEGIN/END, table variable) have poor cardinality estimates."),
("Intermediate","Can you UPDATE through a view?","Yes, with restrictions: the view must map each output row to exactly one base table row (no DISTINCT, no aggregates, no GROUP BY, no UNION). SQL Server traces the update back to the base table. With INSTEAD OF triggers you can make arbitrary views updatable."),
("Intermediate","What is an indexed view and when would you create one?","An indexed view has a unique clustered index physically storing the view's result. It updates automatically when base tables change (write overhead). Use it for large aggregation queries that run constantly and can tolerate the extra storage and write cost. Requirements include SCHEMABINDING, no non-deterministic functions, and two-part names."),
("Advanced","When would CROSS APPLY beat a correlated subquery?","CROSS APPLY lets you use the full power of a FROM clause (JOINs, aggregates with ORDER BY, TOP n) in ways a correlated subquery can't express — particularly TOP n per group. Execution is similar (nested loops), but APPLY can reference TVFs that the optimiser can partially unfold.")])

# ================= DAY 6 =================
# HR schema seed data for reference in queries
HR_SCHEMA = r"""
-- Full HR schema (run once in CompanyDb)
CREATE SCHEMA hr AUTHORIZATION dbo;
GO

CREATE TABLE hr.locations (
    location_id    INT          IDENTITY(1,1) NOT NULL CONSTRAINT PK_locations  PRIMARY KEY,
    city           NVARCHAR(50) NOT NULL,
    state          NVARCHAR(50) NOT NULL,
    country        NVARCHAR(50) NOT NULL CONSTRAINT DF_locations_country DEFAULT 'India'
);

CREATE TABLE hr.departments (
    department_id   INT          IDENTITY(10,10) NOT NULL CONSTRAINT PK_departments PRIMARY KEY,
    department_name NVARCHAR(60) NOT NULL,
    manager_id      INT          NULL,   -- FK added after employees exist
    location_id     INT          NOT NULL CONSTRAINT FK_dept_location REFERENCES hr.locations(location_id)
);

CREATE TABLE hr.jobs (
    job_id      INT            IDENTITY(1,1)  NOT NULL CONSTRAINT PK_jobs PRIMARY KEY,
    job_title   NVARCHAR(60)   NOT NULL,
    min_salary  DECIMAL(10,2)  NOT NULL,
    max_salary  DECIMAL(10,2)  NOT NULL,
    CONSTRAINT CK_jobs_salary CHECK (min_salary > 0 AND max_salary >= min_salary)
);

CREATE TABLE hr.employees (
    employee_id   INT            IDENTITY(1,1)  NOT NULL CONSTRAINT PK_employees PRIMARY KEY,
    first_name    NVARCHAR(40)   NOT NULL,
    last_name     NVARCHAR(40)   NOT NULL,
    email         VARCHAR(100)   NOT NULL CONSTRAINT UQ_emp_email UNIQUE,
    hire_date     DATE           NOT NULL,
    job_id        INT            NOT NULL CONSTRAINT FK_emp_job  REFERENCES hr.jobs(job_id),
    salary        DECIMAL(10,2)  NOT NULL,
    manager_id    INT            NULL     CONSTRAINT FK_emp_mgr  REFERENCES hr.employees(employee_id),
    department_id INT            NULL     CONSTRAINT FK_emp_dept REFERENCES hr.departments(department_id),
    CONSTRAINT CK_emp_salary CHECK (salary > 0)
);

CREATE TABLE hr.salary_history (
    history_id   INT            IDENTITY(1,1)  NOT NULL CONSTRAINT PK_salary_history PRIMARY KEY,
    employee_id  INT            NOT NULL CONSTRAINT FK_sh_emp REFERENCES hr.employees(employee_id),
    old_salary   DECIMAL(10,2)  NOT NULL,
    new_salary   DECIMAL(10,2)  NOT NULL,
    change_date  DATE           NOT NULL,
    changed_by   NVARCHAR(100)  NOT NULL
);

-- Add dept manager FK now that employees table exists
ALTER TABLE hr.departments
    ADD CONSTRAINT FK_dept_manager REFERENCES hr.employees(employee_id);
"""

d6 = day(6, "SAT", "20 HR Practice Queries",
"Work through 20 progressively harder T-SQL queries against the HR schema, covering everything from Week 11 and 12: joins, aggregates, subqueries, CTEs and window functions.",
[("HR schema","Five tables: hr.locations, hr.departments, hr.jobs, hr.employees (with manager_id self-ref), hr.salary_history."),
("Practice query structure","For each query: the question, the SQL solution, and example output — read the expected output before running."),
("Complexity progression","Q1–Q5 aggregate and GROUP BY, Q6–Q10 subqueries, Q11–Q15 CTEs, Q16–Q20 window functions and advanced.")],
["All 20 queries run on the HR schema created on Saturday of Week 11 (or use the seed in this day).",
"Try writing each query yourself before reading the solution.",
"Check your query returns the expected row count and spot-check a few values."],
f'''
<h3>Schema and seed data</h3>
{C(HR_SCHEMA, "hr_schema.sql", lang="sql")}
{C(r"""
-- Sample data (abbreviated — a full 30-row seed in the exercise repo)
INSERT INTO hr.locations VALUES (N'Mumbai', N'Maharashtra', 'India'),
(N'Bengaluru', N'Karnataka', 'India'), (N'Delhi', N'Delhi', 'India'),
(N'Pune', N'Maharashtra', 'India'), (N'Hyderabad', N'Telangana', 'India');

-- Departments (location_id references above):
INSERT INTO hr.departments (department_name, location_id) VALUES
(N'Engineering', 2), (N'Sales', 1), (N'Finance', 4), (N'HR', 1), (N'R&D', 5);
-- (insert jobs then employees similarly — full script in /exercises/week12_seed.sql)
""", "seed_data.sql", lang="sql")}

<h3>Q1 — Headcount and payroll per department</h3>
{C(r"""
SELECT  d.department_name,
        COUNT(*)                                              AS headcount,
        SUM(e.salary)                                        AS total_payroll,
        CAST(AVG(CAST(e.salary AS DECIMAL(14,4))) AS DECIMAL(10,2))
                                                             AS avg_salary
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
GROUP BY d.department_name
ORDER BY total_payroll DESC;
""", "q01.sql", lang="sql")}
{C(r"""
department_name  headcount  total_payroll  avg_salary
---------------  ---------  -------------  ----------
Engineering      12         1140000        95000.00
Sales             8          580000        72500.00
Finance           5          440000        88000.00
HR                4          272000        68000.00
(example output)
""", lang="text")}

<h3>Q2 — Departments with more than 3 employees hired in 2023</h3>
{C(r"""
SELECT  d.department_name,
        COUNT(*) AS new_hires_2023
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
WHERE   YEAR(e.hire_date) = 2023
GROUP BY d.department_name
HAVING  COUNT(*) > 3;
""", "q02.sql", lang="sql")}

<h3>Q3 — Job titles with salary ranges outside the hr.jobs band</h3>
{C(r"""
-- Employees paid below their job's min_salary or above max_salary
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        j.job_title,
        e.salary,
        j.min_salary,
        j.max_salary,
        CASE
            WHEN e.salary < j.min_salary THEN 'Below band'
            WHEN e.salary > j.max_salary THEN 'Above band'
        END AS status
FROM    hr.employees AS e
JOIN    hr.jobs      AS j ON j.job_id = e.job_id
WHERE   e.salary NOT BETWEEN j.min_salary AND j.max_salary;
""", "q03.sql", lang="sql")}

<h3>Q4 — Hiring trend by year (COUNT DISTINCT job titles)</h3>
{C(r"""
SELECT  YEAR(hire_date)        AS hire_year,
        COUNT(*)               AS new_hires,
        COUNT(DISTINCT job_id) AS distinct_job_titles
FROM    hr.employees
GROUP BY YEAR(hire_date)
ORDER BY hire_year;
""", "q04.sql", lang="sql")}
{C(r"""
hire_year  new_hires  distinct_job_titles
---------  ---------  -------------------
2019       3          2
2020       7          4
2021       5          3
2022       8          5
2023       6          3
(example output)
""", lang="text")}

<h3>Q5 — ROLLUP: payroll by state, department and grand total</h3>
{C(r"""
SELECT  COALESCE(l.state,            'ALL STATES')       AS state,
        COALESCE(d.department_name,  'ALL DEPARTMENTS')  AS department,
        SUM(e.salary)                                    AS payroll
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id  = e.department_id
JOIN    hr.locations   AS l ON l.location_id    = d.location_id
GROUP BY ROLLUP(l.state, d.department_name)
ORDER BY l.state, d.department_name;
""", "q05.sql", lang="sql")}

<h3>Q6 — Second-highest salary company-wide (subquery)</h3>
{C(r"""
-- Classic interview question
SELECT MAX(salary) AS second_highest_salary
FROM   hr.employees
WHERE  salary < (SELECT MAX(salary) FROM hr.employees);
""", "q06.sql", lang="sql")}
{C(r"""
second_highest_salary
---------------------
145000.00
(example output)
""", lang="text")}

<h3>Q7 — Employees earning more than their manager</h3>
{C(r"""
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        e.salary                           AS employee_salary,
        m.first_name + ' ' + m.last_name  AS manager_name,
        m.salary                           AS manager_salary,
        e.salary - m.salary                AS gap
FROM    hr.employees AS e
JOIN    hr.employees AS m ON m.employee_id = e.manager_id
WHERE   e.salary > m.salary
ORDER BY gap DESC;
""", "q07.sql", lang="sql")}
{C(r"""
employee_name   employee_salary  manager_name  manager_salary  gap
--------------  ---------------  ------------  --------------  -----
Asha Joshi       180000          Priya Sharma  175000          5000
(example output)
""", lang="text")}

<h3>Q8 — Employees without direct reports (leaf nodes)</h3>
{C(r"""
-- NOT EXISTS: employees who don't appear as anyone's manager
SELECT  e.employee_id,
        e.first_name + ' ' + e.last_name  AS employee_name
FROM    hr.employees AS e
WHERE   NOT EXISTS
        (SELECT 1 FROM hr.employees AS sub WHERE sub.manager_id = e.employee_id)
ORDER BY e.last_name;
""", "q08.sql", lang="sql")}

<h3>Q9 — Departments with average salary above company average (subquery in HAVING)</h3>
{C(r"""
SELECT  d.department_name,
        CAST(AVG(CAST(e.salary AS DECIMAL(14,4))) AS DECIMAL(10,2))  AS avg_sal
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
GROUP BY d.department_name
HAVING  AVG(CAST(e.salary AS DECIMAL(14,4))) >
        (SELECT AVG(CAST(salary AS DECIMAL(14,4))) FROM hr.employees)
ORDER BY avg_sal DESC;
""", "q09.sql", lang="sql")}

<h3>Q10 — Salary gap to manager (scalar subquery per row)</h3>
{C(r"""
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        e.salary,
        (
            SELECT m.salary
            FROM   hr.employees AS m
            WHERE  m.employee_id = e.manager_id
        )                                  AS manager_salary,
        (
            SELECT m.salary - e.salary
            FROM   hr.employees AS m
            WHERE  m.employee_id = e.manager_id
        )                                  AS gap_to_manager
FROM    hr.employees AS e
WHERE   e.manager_id IS NOT NULL
ORDER BY gap_to_manager DESC;
""", "q10.sql", lang="sql")}

<h3>Q11 — Full org chart with level and path (recursive CTE)</h3>
{C(r"""
WITH org AS (
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name  AS name,
            e.manager_id,
            0                                  AS lvl,
            CAST(e.first_name + ' ' + e.last_name AS NVARCHAR(2000))
                                               AS path
    FROM    hr.employees AS e
    WHERE   e.manager_id IS NULL
    UNION ALL
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name,
            e.manager_id,
            o.lvl + 1,
            CAST(o.path + N' > ' + e.first_name + N' ' + e.last_name AS NVARCHAR(2000))
    FROM    hr.employees AS e
    JOIN    org          AS o ON o.employee_id = e.manager_id
)
SELECT  REPLICATE(N'    ', lvl) + name  AS indented_name,
        lvl                             AS level,
        path
FROM    org
ORDER BY path;
""", "q11.sql", lang="sql")}
{C(r"""
indented_name                              level  path
-----------------------------------------  -----  ------------------------------------------------
Priya Sharma                               0      Priya Sharma
    Asha Joshi                             1      Priya Sharma > Asha Joshi
        Karan Mehta                        2      Priya Sharma > Asha Joshi > Karan Mehta
    Vikram Nair                            1      Priya Sharma > Vikram Nair
(example output)
""", lang="text")}

<h3>Q12 — Number of salary raises per employee (CTE + count)</h3>
{C(r"""
WITH raise_counts AS (
    SELECT  employee_id,
            COUNT(*) AS num_raises,
            MIN(change_date) AS first_raise,
            MAX(change_date) AS latest_raise
    FROM    hr.salary_history
    GROUP BY employee_id
)
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        COALESCE(rc.num_raises, 0)         AS num_raises,
        rc.first_raise,
        rc.latest_raise
FROM    hr.employees    AS e
LEFT JOIN raise_counts  AS rc ON rc.employee_id = e.employee_id
ORDER BY num_raises DESC, e.last_name;
""", "q12.sql", lang="sql")}

<h3>Q13 — PERCENTILE_CONT median salary per department (CTE + WITHIN GROUP)</h3>
{C(r"""
-- PERCENTILE_CONT is an ordered-set aggregate (not a window function)
SELECT DISTINCT
        d.department_name,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e.salary)
            OVER (PARTITION BY e.department_id)   AS median_salary
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
ORDER BY department_name;
""", "q13.sql", lang="sql")}
{C(r"""
department_name  median_salary
---------------  -------------
Engineering      95000.00
Finance          88000.00
HR               68500.00
Sales            72000.00
(example output)
""", lang="text")}
{tip("PERCENTILE_CONT returns the interpolated median (average of two middle values when count is even). PERCENTILE_DISC returns the nearest actual value from the data. Both are ordered-set aggregates — they appear in SELECT with OVER but cannot be used in a plain HAVING clause.")}

<h3>Q14 — Running headcount by hire month</h3>
{C(r"""
WITH monthly_hires AS (
    SELECT  DATEFROMPARTS(YEAR(hire_date), MONTH(hire_date), 1)  AS hire_month,
            COUNT(*)                                              AS new_hires
    FROM    hr.employees
    GROUP BY DATEFROMPARTS(YEAR(hire_date), MONTH(hire_date), 1)
)
SELECT  hire_month,
        new_hires,
        SUM(new_hires)
            OVER (ORDER BY hire_month
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)  AS running_headcount
FROM    monthly_hires
ORDER BY hire_month;
""", "q14.sql", lang="sql")}
{C(r"""
hire_month   new_hires  running_headcount
-----------  ---------  -----------------
2019-06-01   3          3
2019-09-01   2          5
2020-01-01   4          9
2020-07-01   3          12
(example output)
""", lang="text")}

<h3>Q15 — Employees with tenure over 5 years (CTE for readability)</h3>
{C(r"""
WITH tenure AS (
    SELECT  employee_id,
            first_name + ' ' + last_name  AS employee_name,
            hire_date,
            DATEDIFF(YEAR, hire_date, GETDATE())  AS tenure_years
    FROM    hr.employees
)
SELECT employee_name, hire_date, tenure_years
FROM   tenure
WHERE  tenure_years > 5
ORDER BY tenure_years DESC;
""", "q15.sql", lang="sql")}

<h3>Q16 — Salary rank within department (ROW_NUMBER / RANK / DENSE_RANK)</h3>
{C(r"""
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        d.department_name,
        e.salary,
        ROW_NUMBER()  OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS row_num,
        RANK()        OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS rnk,
        DENSE_RANK()  OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS dense_rnk
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
ORDER BY d.department_name, e.salary DESC;
""", "q16.sql", lang="sql")}

<h3>Q17 — Top 3 earners per department</h3>
{C(r"""
WITH ranked AS (
    SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
            d.department_name,
            e.salary,
            DENSE_RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS dr
    FROM    hr.employees   AS e
    JOIN    hr.departments AS d ON d.department_id = e.department_id
)
SELECT department_name, employee_name, salary
FROM   ranked
WHERE  dr <= 3
ORDER BY department_name, salary DESC;
""", "q17.sql", lang="sql")}
{C(r"""
department_name  employee_name    salary
---------------  ---------------  -------
Engineering      Asha Joshi       180000
Engineering      Vikram Nair      145000
Engineering      Priya Desai      120000
Finance          Pooja Iyer       115000
Finance          Rahul Gupta       98000
Finance          Suresh Kulkarni   88000
(example output)
""", lang="text")}

<h3>Q18 — Salary trajectory per employee: LAG and % change</h3>
{C(r"""
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        sh.change_date,
        sh.old_salary,
        sh.new_salary,
        sh.new_salary - sh.old_salary       AS absolute_increase,
        CAST((sh.new_salary - sh.old_salary) * 100.0 / NULLIF(sh.old_salary, 0)
             AS DECIMAL(5,2))               AS pct_increase,
        LAG(sh.new_salary) OVER (PARTITION BY sh.employee_id ORDER BY sh.change_date)
                                            AS salary_before_this_raise
FROM    hr.salary_history AS sh
JOIN    hr.employees      AS e ON e.employee_id = sh.employee_id
ORDER BY sh.employee_id, sh.change_date;
""", "q18.sql", lang="sql")}

<h3>Q19 — Salary band distribution using NTILE</h3>
{C(r"""
WITH bands AS (
    SELECT  employee_id,
            first_name + ' ' + last_name  AS employee_name,
            salary,
            NTILE(4) OVER (ORDER BY salary)  AS quartile
    FROM    hr.employees
)
SELECT  quartile,
        COUNT(*)                                                   AS headcount,
        MIN(salary)                                                AS min_sal,
        MAX(salary)                                                AS max_sal,
        CAST(AVG(CAST(salary AS DECIMAL(14,4))) AS DECIMAL(10,2)) AS avg_sal
FROM    bands
GROUP BY quartile
ORDER BY quartile;
""", "q19.sql", lang="sql")}
{C(r"""
quartile  headcount  min_sal  max_sal  avg_sal
--------  ---------  -------  -------  --------
1         7          55000    68000    61142.86
2         8          70000    82000    75250.00
3         7          85000    98000    91142.86
4         7          105000   180000   130857.14
(example output)
""", lang="text")}

<h3>Q20 — Department-level median vs individual salary deviation</h3>
{C(r"""
-- How far is each employee from their department's median salary?
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        d.department_name,
        e.salary,
        CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e2.salary)
            OVER (PARTITION BY e.department_id) AS DECIMAL(10,2))  AS dept_median,
        e.salary - CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e2.salary)
            OVER (PARTITION BY e.department_id) AS DECIMAL(10,2))  AS deviation_from_median
FROM    hr.employees   AS e
JOIN    hr.departments AS d  ON d.department_id = e.department_id
JOIN    hr.employees   AS e2 ON e2.department_id = e.department_id   -- self-join for PERCENTILE
ORDER BY d.department_name, deviation_from_median DESC;
""", "q20.sql", lang="sql")}
{C(r"""
employee_name     department_name  salary   dept_median  deviation_from_median
----------------  ---------------  -------  -----------  ---------------------
Asha Joshi        Engineering      180000   95000.00     85000.00
Vikram Nair       Engineering      145000   95000.00     50000.00
...
Rohit Verma       Engineering       62000   95000.00    -33000.00
(example output)
""", lang="text")}
''',
iqs=[("Basic","What is the difference between WHERE and HAVING?","WHERE filters rows before grouping; HAVING filters groups after aggregation. HAVING can reference aggregate functions; WHERE cannot. For performance, use WHERE whenever the condition doesn't involve an aggregate."),
("Basic","Explain the NOT IN NULL trap with an example.","If the subquery inside NOT IN returns any NULL value, the predicate becomes UNKNOWN for every row (NULL <> x is UNKNOWN, not FALSE), so NOT IN returns zero rows. Fix: use NOT EXISTS, or add WHERE col IS NOT NULL to the inner SELECT."),
("Intermediate","What is PERCENTILE_CONT and how is it different from AVG?","PERCENTILE_CONT computes the interpolated median (or any percentile) of a column. For an even count it averages the two middle values. AVG sums all values and divides by count — it is sensitive to outliers. For skewed salary distributions, median (PERCENTILE_CONT(0.5)) is a more representative 'typical' salary."),
("Intermediate","How does ROW_NUMBER differ from RANK when there are salary ties?","ROW_NUMBER gives every row a unique number regardless of ties (1,2,3,4). RANK gives tied rows the same number and skips subsequent numbers (1,2,2,4). DENSE_RANK doesn't skip (1,2,2,3). For top-N filtering DENSE_RANK ensures ties at boundary position are all included.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Revise and redo the hardest queries",
"Redo the 5 hardest queries from yesterday's set entirely from memory using only the hints, then take the 5-question quiz.",
[("Active recall","Writing a query from memory, then checking against the reference — far more effective than re-reading."),
("Derivation","Working from first principles: what table, what join, what clause?"),
("Query decomposition","Breaking a hard query into its parts: group first, then window, then filter.")],
["Close yesterday's notes before attempting each query.",
"Use only the hint for each query.",
"If you get stuck, re-read only the concept section for that technique, then try again."],
f'''
<h3>Revision plan (≈4 hours)</h3>
{table(["Time","Task"],[
["45 min","Redo Q6, Q11, Q13, Q17, Q20 from memory using only the hints below"],
["30 min","Compare your solutions with yesterday's; note every difference"],
["45 min","Re-read the parts of Days 1–5 that your solutions missed"],
["45 min","Quiz (below) — write answers on paper first"],
["45 min","Run all 20 queries against your SQL Server; fix any that differ from expected output"],
["30 min","Write 3 real-world variations of Q17 (top-3 per month, per job title, per manager)"]])}

<h3>Hints for the 5 hardest queries</h3>
<h4>Q6 — Second-highest salary</h4>
<details><summary>Hint</summary>
<p>Find the MAX salary where that salary is less than the overall MAX. Use a scalar subquery.</p>
</details>
<details><summary>Solution</summary>
{C(r"""
SELECT MAX(salary) AS second_highest_salary
FROM   hr.employees
WHERE  salary < (SELECT MAX(salary) FROM hr.employees);
""", lang="sql")}
</details>

<h4>Q11 — Recursive org chart</h4>
<details><summary>Hint</summary>
<p>Anchor: employees where manager_id IS NULL. Recursive member: JOIN hr.employees to the CTE on employee_id = manager_id. Carry a path string using CAST to NVARCHAR(2000).</p>
</details>
<details><summary>Solution</summary>
{C(r"""
WITH org AS (
    SELECT  employee_id,
            first_name + ' ' + last_name  AS name,
            0                              AS lvl,
            CAST(first_name + ' ' + last_name AS NVARCHAR(2000))  AS path
    FROM    hr.employees WHERE manager_id IS NULL
    UNION ALL
    SELECT  e.employee_id,
            e.first_name + ' ' + e.last_name,
            o.lvl + 1,
            CAST(o.path + N' > ' + e.first_name + N' ' + e.last_name AS NVARCHAR(2000))
    FROM    hr.employees AS e JOIN org AS o ON o.employee_id = e.manager_id
)
SELECT  REPLICATE(N'  ', lvl) + name  AS indented_name, lvl, path
FROM    org ORDER BY path;
""", lang="sql")}
</details>

<h4>Q13 — PERCENTILE_CONT median per department</h4>
<details><summary>Hint</summary>
<p>Use PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) OVER (PARTITION BY department_id). Wrap in SELECT DISTINCT to collapse the per-row repetition.</p>
</details>
<details><summary>Solution</summary>
{C(r"""
SELECT DISTINCT
        d.department_name,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY e.salary)
            OVER  (PARTITION BY e.department_id)   AS median_salary
FROM    hr.employees   AS e
JOIN    hr.departments AS d ON d.department_id = e.department_id
ORDER BY department_name;
""", lang="sql")}
</details>

<h4>Q17 — Top 3 per department using DENSE_RANK</h4>
<details><summary>Hint</summary>
<p>CTE with DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dr. Outer query: WHERE dr &lt;= 3.</p>
</details>
<details><summary>Solution</summary>
{C(r"""
WITH ranked AS (
    SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
            d.department_name,
            e.salary,
            DENSE_RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC)  AS dr
    FROM    hr.employees   AS e
    JOIN    hr.departments AS d ON d.department_id = e.department_id
)
SELECT department_name, employee_name, salary
FROM   ranked WHERE dr <= 3
ORDER BY department_name, salary DESC;
""", lang="sql")}
</details>

<h4>Q20 — Deviation from department median</h4>
<details><summary>Hint</summary>
<p>Self-join hr.employees to itself on department_id so PERCENTILE_CONT can aggregate over the department's salaries. The salary deviation is e.salary minus the PERCENTILE_CONT result.</p>
</details>
<details><summary>Solution</summary>
{C(r"""
SELECT  e.first_name + ' ' + e.last_name  AS employee_name,
        d.department_name,
        e.salary,
        CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e2.salary)
            OVER (PARTITION BY e.department_id) AS DECIMAL(10,2))  AS dept_median,
        e.salary - CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e2.salary)
            OVER (PARTITION BY e.department_id) AS DECIMAL(10,2))  AS deviation
FROM    hr.employees   AS e
JOIN    hr.departments AS d  ON d.department_id = e.department_id
JOIN    hr.employees   AS e2 ON e2.department_id = e.department_id
ORDER BY d.department_name, deviation DESC;
""", lang="sql")}
</details>

<h3>5-question quiz</h3>
<details><summary>Q1. What does DENSE_RANK() OVER (ORDER BY salary DESC) return for salaries 180000, 145000, 145000, 120000?</summary>
{C(r"""
-- Predict before reading:
SELECT salary,
       DENSE_RANK() OVER (ORDER BY salary DESC) AS dr
FROM (VALUES (180000),(145000),(145000),(120000)) AS t(salary);
""", lang="sql")}
<b>1, 2, 2, 3.</b> DENSE_RANK gives tied rows the same rank and does not skip the next number.</details>

<details><summary>Q2. How many rows does this return?</summary>
{C(r"""
SELECT department_id
FROM   hr.employees
WHERE  department_id NOT IN (SELECT manager_id FROM hr.employees);
""", lang="sql")}
<b>0 rows</b> (if any employee has manager_id = NULL). NOT IN with a NULL in the list produces UNKNOWN for every comparison, so no rows pass the WHERE filter. Use NOT EXISTS instead.</details>

<details><summary>Q3. Which FRAME clause gives a strict 3-row moving average regardless of ties?</summary>
<b>ROWS BETWEEN 2 PRECEDING AND CURRENT ROW.</b> ROWS counts physical row positions. RANGE would group tied ORDER BY values together, possibly including more than 3 rows at a boundary.</details>

<details><summary>Q4. What is the maximum recursion depth for a recursive CTE by default, and how do you change it?</summary>
<b>100 levels.</b> Change it with the query hint at the end of the statement: <code>OPTION (MAXRECURSION 500)</code>. Set to 0 for unlimited (risk on cyclic data).</details>

<details><summary>Q5. A CROSS APPLY returned fewer rows than the FROM table. Why?</summary>
<b>Because CROSS APPLY drops rows from the left side when the right side returns no rows</b> — the same behaviour as INNER JOIN. Use OUTER APPLY to keep all left rows with NULLs when the right side is empty.</details>

<div class="note tip"><b>Next week:</b> Week 13 — Programmability and transactions: stored procedures, variables, control flow (IF/WHILE/TRY-CATCH), transactions (BEGIN/COMMIT/ROLLBACK), isolation levels and the sales order micro-project.</div>
''',
iqs=[("Basic","What is the difference between ROW_NUMBER and DENSE_RANK?","ROW_NUMBER gives each row a unique sequential number, never ties. DENSE_RANK gives tied rows the same number and does not skip the next number (1,1,2 for a two-way tie). Use ROW_NUMBER for de-duplication, DENSE_RANK for leaderboards where ties should share a position."),
("Basic","What is PERCENTILE_CONT and when is it more useful than AVG?","PERCENTILE_CONT computes the interpolated value at a given percentile (0.5 for median). Unlike AVG it is not distorted by extreme outliers — a CEO salary at ₹1.8 crore barely moves the median but triples the average. Use it when reporting 'typical' values in skewed distributions like salaries."),
("Intermediate","Explain when you would use a CTE vs a temp table.","CTE: single-statement scope, great for readability and recursive queries, no indexing. Temp table: persists for the session, can be indexed, has statistics, ideal for large intermediate results used multiple times. When a CTE is referenced twice in a query and the intermediate result is expensive to compute, materialise it in a temp table first."),
("Intermediate","How do you calculate the second-highest value without a window function?","SELECT MAX(col) FROM table WHERE col < (SELECT MAX(col) FROM table). The inner subquery finds the maximum; the outer query finds the maximum among all values strictly less than it, which is the second-highest. Using DENSE_RANK = 2 in a CTE handles ties more cleanly.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","GROUP BY, HAVING and aggregates","GROUP BY","Aggregates, COUNT(DISTINCT), WHERE vs HAVING, multi-column groups, ROLLUP awareness.","2 hrs"),
 (2,"TUE","Subqueries","Subqueries","Scalar, column, table, correlated, EXISTS vs IN, NOT IN NULL trap, derived tables.","2 hrs"),
 (3,"WED","Common Table Expressions","CTEs","Chained CTEs, recursive org charts, MAXRECURSION, CTE vs temp table.","2 hrs"),
 (4,"THU","Window functions","Window functions","ROW_NUMBER/RANK/DENSE_RANK/NTILE, LAG/LEAD, running totals, moving averages, top-N per group.","2 hrs"),
 (5,"FRI","Views, TVFs and APPLY","Views &amp; TVFs","SCHEMABINDING, ITVF vs MSTVF, scalar UDF inlining, CROSS/OUTER APPLY.","2 hrs"),
 (6,"SAT","20 HR Practice Queries","20 HR queries","Full HR schema + 20 progressive queries from aggregates to window functions.","4 hrs"),
 (7,"SUN","Revise and redo the hardest queries","Revision","Redo 5 hardest from memory, hints then solutions, 5-question quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week12.html", 12,
      "Week 12 — Advanced T-SQL",
      "Phase 2", "~18 hrs",
      ["Phase 2 · Week 12 of 74", ".NET 8 LTS / 9", "SQL Server 2022", "~18 hrs", "20 HR queries"],
      "Every real query you write in production — finding outliers, ranking employees, computing running totals, traversing org charts — relies on the techniques in this week: GROUP BY with HAVING, subqueries at every level, CTEs including recursive ones, window functions and table-valued functions. By Sunday you will have written 20 non-trivial HR queries from scratch.",
      cards, days)
print("built")
