import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Stored procedures: parameters, OUTPUT, RETURN and EXEC",
"Write, alter and call stored procedures with input parameters, defaults, OUTPUT parameters and return codes — and pick up the habits (SET NOCOUNT ON, no sp_ prefix) that mark production-quality T-SQL.",
[("Stored procedure","A named, precompiled batch of T-SQL saved in the database, called with <code>EXEC</code>. Can take parameters, return result sets, OUTPUT values and an integer return code."),
("Batch","A set of statements sent to SQL Server as one unit. In scripts, <code>GO</code> (a client-tool word, not T-SQL) separates batches."),
("CREATE OR ALTER","Creates the procedure if missing, otherwise replaces its body while keeping permissions. SQL Server 2016 SP1+."),
("Input parameter","A typed value passed into the proc: <code>@DepartmentId INT</code>. Parameters are the only safe way to pass user input (no string concatenation)."),
("Default parameter","A parameter with a declared default (<code>@Top INT = 10</code>) that the caller may omit or pass as <code>DEFAULT</code>."),
("OUTPUT parameter","A parameter the proc writes back to the caller. Marked <code>OUTPUT</code> in the proc <i>and</i> at the call site."),
("RETURN code","An integer the proc hands back with <code>RETURN n</code>; by convention 0 = success, non-zero = a status/error code. Captured with <code>EXEC @rc = proc</code>."),
("EXEC / EXECUTE","Runs a procedure (or a string — dynamic SQL, used sparingly). Parameters can be positional or named."),
("SCOPE_IDENTITY()","The last identity value generated in the current scope — the right way to grab a new row's id inside a proc."),
("SET NOCOUNT ON","Suppresses the \"(n rows affected)\" message per statement, cutting network chatter. First line of almost every proc."),
("Plan cache","Where SQL Server keeps compiled execution plans. A proc's plan is compiled on first execution and reused."),
("Parameter sniffing","At first compile, SQL Server \"sniffs\" the actual parameter values and optimises the plan for them — great until a very different value reuses the same plan."),
("sp_ prefix","Reserved by convention for system procedures in <code>master</code>. User procs named <code>sp_…</code> cost an extra lookup and risk name collisions — use <code>usp_</code> or none."),
("OBJECT_DEFINITION","Returns a module's source: <code>SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.usp_X'))</code>. <code>sys.procedures</code> lists all procs.")],
["A proc gives you: one place for logic, parameterisation (no SQL injection), a cached plan, and a security boundary (grant EXECUTE, not table access).",
"<code>CREATE OR ALTER</code> beats DROP + CREATE: permissions and dependencies survive.",
"Call with <b>named</b> parameters: <code>EXEC usp_X @DepartmentId = 2</code> — positional calls break silently when parameters are reordered.",
"OUTPUT must appear in <b>both</b> places: the parameter declaration and the call site, or the value is silently not copied back.",
"RETURN can only carry an int. Data belongs in result sets or OUTPUT parameters.",
"Start every proc with <code>SET NOCOUNT ON;</code> and never name it <code>sp_…</code>."],
f'''
<p class="muted">This week keeps using the HR database you built in Weeks 11–12. Quick reference (adapt names if yours differ):</p>
{C(r"""
USE HR;
GO
-- dbo.Departments (DepartmentId INT IDENTITY PK, Name NVARCHAR(50) UNIQUE)
-- dbo.Employees   (EmployeeId INT IDENTITY PK, FirstName, LastName, Email UNIQUE,
--                  DepartmentId INT FK -> Departments, Salary DECIMAL(10,2),
--                  HireDate DATE, City NVARCHAR(50), IsActive BIT DEFAULT 1)
""", "schema-recap.sql", lang="sql")}

<h3>1. Why stored procedures?</h3>
<p>So far you've sent ad-hoc SELECTs from a query window. In a real system the application calls named, parameterised procedures instead:</p>
{table(["Benefit","Why it matters"],[
["One definition","The \"employees by department\" query lives in one place, not pasted into five C# files."],
["Parameterisation","Values travel as typed parameters — SQL injection through string concatenation becomes impossible."],
["Plan reuse","The plan is compiled once and cached; later calls skip compilation."],
["Security boundary","Grant users <code>EXECUTE</code> on procs and no direct table access at all."],
["Less network traffic","Multi-statement logic runs server-side in one round trip."]])}
{C(r"""
CREATE OR ALTER PROCEDURE dbo.usp_GetEmployeesByDepartment
    @DepartmentId INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT EmployeeId, FirstName, LastName, Salary
    FROM dbo.Employees
    WHERE DepartmentId = @DepartmentId
      AND IsActive = 1
    ORDER BY LastName;
END
GO

EXEC dbo.usp_GetEmployeesByDepartment @DepartmentId = 2;
""", "first-proc.sql", lang="sql")}
{C(r"""
-- Example output (your Week 11 seed data decides the rows)
EmployeeId  FirstName   LastName    Salary
----------- ----------- ----------- -----------
4           Divya       Kulkarni    58000.00
2           Rahul       Mehta       72500.00
""", lang="text")}
{tip("The body between <code>AS</code> and the end of the batch is the proc. Wrapping it in <code>BEGIN … END</code> is optional but makes the boundary explicit — always do it.")}

<h3>2. Default parameters and optional filters</h3>
{C(r"""
CREATE OR ALTER PROCEDURE dbo.usp_SearchEmployees
    @Search       NVARCHAR(50)  = NULL,     -- NULL means "don't filter on this"
    @DepartmentId INT           = NULL,
    @MinSalary    DECIMAL(10,2) = 0
AS
BEGIN
    SET NOCOUNT ON;

    SELECT e.EmployeeId, e.FirstName, e.LastName, d.Name AS Department, e.Salary
    FROM dbo.Employees e
    JOIN dbo.Departments d ON d.DepartmentId = e.DepartmentId
    WHERE (@Search IS NULL OR e.FirstName LIKE N'%' + @Search + N'%'
                           OR e.LastName  LIKE N'%' + @Search + N'%')
      AND (@DepartmentId IS NULL OR e.DepartmentId = @DepartmentId)
      AND e.Salary >= @MinSalary
      AND e.IsActive = 1
    ORDER BY e.LastName;
END
GO

EXEC dbo.usp_SearchEmployees;                                    -- all defaults: everyone
EXEC dbo.usp_SearchEmployees @DepartmentId = 2;                  -- named (recommended)
EXEC dbo.usp_SearchEmployees N'ra', 2, 50000;                    -- positional: fragile
EXEC dbo.usp_SearchEmployees @Search = DEFAULT, @MinSalary = 60000;  -- explicit default
""", "search-employees.sql", lang="sql")}
{warn("The <code>(@p IS NULL OR col = @p)</code> \"catch-all\" pattern is handy but produces one plan for very different searches — a classic parameter-sniffing victim. For now add <code>OPTION (RECOMPILE)</code> to the SELECT if it gets slow; Week 14 explains why.", "Note")}

<h3>3. OUTPUT parameters</h3>
<p>Use OUTPUT when the caller needs a scalar back <i>in addition to</i> (or instead of) a result set — a new id, a count, a total.</p>
{C(r"""
CREATE OR ALTER PROCEDURE dbo.usp_HireEmployee
    @FirstName     NVARCHAR(50),
    @LastName      NVARCHAR(50),
    @Email         NVARCHAR(100),
    @DepartmentId  INT,
    @Salary        DECIMAL(10,2),
    @NewEmployeeId INT OUTPUT                 -- marked OUTPUT here...
AS
BEGIN
    SET NOCOUNT ON;

    INSERT dbo.Employees (FirstName, LastName, Email, DepartmentId, Salary, HireDate)
    VALUES (@FirstName, @LastName, @Email, @DepartmentId, @Salary, CAST(GETDATE() AS DATE));

    SET @NewEmployeeId = SCOPE_IDENTITY();    -- identity from THIS scope, not a trigger's
END
GO

DECLARE @id INT;
EXEC dbo.usp_HireEmployee
     @FirstName = N'Kavya', @LastName = N'Reddy', @Email = N'kavya.reddy@lnw-demo.in',
     @DepartmentId = 2, @Salary = 61000,
     @NewEmployeeId = @id OUTPUT;             -- ...and OUTPUT again here
SELECT @id AS NewEmployeeId;
""", "hire-employee.sql", lang="sql")}
{C(r"""
NewEmployeeId
-------------
11
""", lang="text")}
{warn("Forget <code>OUTPUT</code> at the call site and the call still succeeds — but <code>@id</code> stays NULL. No error, just a silently missing value. This is one of the most common proc bugs.", "Gotcha")}
<p>Prefer <code>SCOPE_IDENTITY()</code> over <code>@@IDENTITY</code>: <code>@@IDENTITY</code> returns the last identity in the <i>session</i>, which can be a different table's id if a trigger inserted somewhere.</p>

<h3>4. RETURN codes</h3>
{C(r"""
CREATE OR ALTER PROCEDURE dbo.usp_DeactivateEmployee
    @EmployeeId INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM dbo.Employees WHERE EmployeeId = @EmployeeId)
        RETURN 1;                 -- not found
    IF EXISTS (SELECT 1 FROM dbo.Employees WHERE EmployeeId = @EmployeeId AND IsActive = 0)
        RETURN 2;                 -- already inactive

    UPDATE dbo.Employees SET IsActive = 0 WHERE EmployeeId = @EmployeeId;
    RETURN 0;                     -- success (also the default when you fall off the end)
END
GO

DECLARE @rc INT;
EXEC @rc = dbo.usp_DeactivateEmployee @EmployeeId = 999;
SELECT @rc AS ReturnCode;         -- 1
""", "return-codes.sql", lang="sql")}
{table(["Channel","Carries","Use for"],[
["Result set(s)","Rows and columns","The data the caller asked for"],
["OUTPUT parameter","One typed scalar each","New ids, computed totals, counts"],
["RETURN code","One <code>int</code> only","Coarse status (0 ok / non-zero code)"],
["THROW (tomorrow)","An error","Actual failures the caller must not ignore"]])}
{tip("Modern code mostly uses result sets + OUTPUT + THROW. RETURN codes survive in older codebases and scripts — know them, read them, but don't encode rich errors in them.")}

<h3>5. Getting proc results into tables, and reading proc definitions</h3>
{C(r"""
CREATE OR ALTER PROCEDURE dbo.usp_TopEarners
    @Top INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@Top) EmployeeId, FirstName + N' ' + LastName AS FullName, Salary
    FROM dbo.Employees
    WHERE IsActive = 1
    ORDER BY Salary DESC;
END
GO

-- Capture a proc's result set into a temp table (columns must match)
CREATE TABLE #TopPaid (EmployeeId INT, FullName NVARCHAR(101), Salary DECIMAL(10,2));
INSERT #TopPaid
EXEC dbo.usp_TopEarners @Top = 3;

SELECT * FROM #TopPaid;

-- Inspect what exists
SELECT name, create_date, modify_date FROM sys.procedures ORDER BY name;
SELECT OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_TopEarners'));   -- the source text
EXEC sp_helptext N'dbo.usp_TopEarners';                       -- line by line
""", "insert-exec.sql", lang="sql")}

<h3>6. Habits: SET NOCOUNT ON, naming, and the sniffing teaser</h3>
{ul(["<b>SET NOCOUNT ON</b> — without it every statement sends a \"rows affected\" message to the client; chatty and occasionally confuses old data-access layers that mistake the message for a result.",
"<b>Never <code>sp_</code></b> — SQL Server first looks for <code>sp_…</code> names in <code>master</code>, so you pay a lookup detour, and a future system proc with your name wins. Use <code>usp_</code> (user stored procedure) like this course, or a clean verb-noun name.",
"<b>Schema-qualify</b> — write <code>dbo.usp_X</code> when creating and calling; it avoids resolution ambiguity and helps plan reuse.",
"<b>One proc, one purpose</b> — a proc that takes 14 optional parameters and 6 modes is five procs in a trench coat."])}
<p><b>Parameter sniffing in one paragraph:</b> the first call's parameter values shape the cached plan. <code>EXEC usp_SearchEmployees @DepartmentId = 7</code> (3 employees) compiles a plan ideal for 3 rows; when the next call asks for department 1 (4,000 employees) it reuses that tiny-result plan and crawls. Fixes — <code>OPTION (RECOMPILE)</code>, <code>OPTIMIZE FOR</code>, rewriting catch-all filters — are a Week 14 topic. Today, just be able to name the phenomenon.</p>
''',
["Calling with positional parameters, then reordering the parameter list later — silent wrong results.",
"Forgetting <code>OUTPUT</code> at the call site (the proc runs; the variable stays NULL).",
"Using <code>@@IDENTITY</code> instead of <code>SCOPE_IDENTITY()</code>.",
"Naming user procs <code>sp_…</code>.",
"Building the WHERE clause by concatenating strings instead of using parameters — SQL injection and no plan reuse."],
("40 min", ["Write <code>dbo.usp_GetDepartmentSummary @DepartmentId INT</code> returning one row: department name, employee count, min/avg/max salary. Add OUTPUT parameter <code>@EmployeeCount INT</code> and verify both channels agree.",
"Write <code>dbo.usp_GiveRaise @EmployeeId INT, @Percent DECIMAL(5,2), @NewSalary DECIMAL(10,2) OUTPUT</code> with RETURN 1 when the employee doesn't exist and RETURN 2 when <code>@Percent</code> is outside 0–50.",
"Use INSERT…EXEC to capture <code>usp_TopEarners @Top = 5</code> into <code>#TopPaid</code>, then join it back to Departments to show each top earner's department name."]),
[("What does SET NOCOUNT ON actually suppress?","The DONE_IN_PROC \"(n rows affected)\" messages sent after each statement. Result sets and errors still flow normally; you just drop the chatter."),
("Why is the sp_ prefix an anti-pattern?","Names starting with sp_ are searched in the master database first, costing an extra lookup, and may collide with current or future system procedures that would then take precedence."),
("How do you get a new identity value out of an insert proc, and why that function?","SET an OUTPUT parameter to SCOPE_IDENTITY() right after the INSERT. It returns the last identity generated in the current scope, unlike @@IDENTITY which can return a value generated by a trigger on another table.")],
[("Basic","What are the advantages of stored procedures over ad-hoc SQL from the application?","Centralised logic (one definition to fix or tune), enforced parameterisation (no injection via concatenation), execution plan reuse, a security boundary (grant EXECUTE without table permissions), and fewer round trips for multi-statement operations."),
("Basic","What is the difference between an OUTPUT parameter and a RETURN value?","RETURN carries exactly one int, conventionally 0 for success, and can't be skipped — every proc returns one. OUTPUT parameters carry any number of typed scalars (ids, totals, strings) and must be marked OUTPUT both in the signature and at the call site."),
("Basic","What does CREATE OR ALTER do and when is it available?","Since SQL Server 2016 SP1 it creates the module if absent or alters it in place if present — unlike DROP + CREATE it keeps existing permissions, and unlike plain ALTER it doesn't fail on first deployment. It works for procs, views, functions and triggers."),
("Intermediate","What is parameter sniffing?","When a proc is first compiled, the optimiser uses the actual parameter values to estimate row counts and choose the plan. The plan is cached and reused for later calls with very different values, which can make it badly wrong (e.g. a plan built for 3 rows scanning for 4 million). Mitigations: OPTION (RECOMPILE), OPTIMIZE FOR, dynamic SQL per shape, or splitting the proc."),
("Intermediate","How would you lock down a database so applications can only use procs?","Create a role, GRANT EXECUTE ON SCHEMA::dbo (or per proc) to it, add the app login's user to the role, and grant no SELECT/INSERT/UPDATE/DELETE on tables. Ownership chaining lets dbo-owned procs touch dbo-owned tables without the caller holding table permissions."),
("Intermediate","Can a stored procedure return multiple result sets? How does a caller consume them?","Yes — each SELECT that reaches the client adds a result set, in order. ADO.NET readers walk them with SqlDataReader.NextResult(); Dapper uses QueryMultiple; EF Core needs raw ADO.NET or stitching. Keep the order and shapes stable: callers bind by position.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Error handling: TRY/CATCH, THROW vs RAISERROR, XACT_STATE",
"Catch and report T-SQL errors properly: TRY/CATCH with the ERROR_* functions, THROW for raising and rethrowing, and XACT_ABORT + XACT_STATE so failures never leave a transaction half-open.",
[("TRY…CATCH","<code>BEGIN TRY … END TRY BEGIN CATCH … END CATCH</code>. A runtime error (severity &gt; 10) inside TRY jumps to CATCH instead of aborting the batch."),
("ERROR_NUMBER()","In CATCH: the error's number. System errors are &lt; 50000; your THROWn errors are ≥ 50000."),
("ERROR_MESSAGE()","In CATCH: the full error text, with substituted values."),
("ERROR_SEVERITY() / ERROR_STATE()","Severity (how bad) and state (where/why variant) of the caught error."),
("ERROR_LINE() / ERROR_PROCEDURE()","Line number and module name where the error happened — gold for logging."),
("Severity","0–10 informational (not catchable), 11–16 user-correctable errors, 17–19 resource errors, 20–25 fatal (connection killed, not catchable in that session)."),
("THROW","Modern (2012+) way to raise an error: <code>THROW 50001, N'msg', 1;</code> — or bare <code>THROW;</code> inside CATCH to rethrow the original. Always severity 16; always terminates the batch."),
("RAISERROR","Older raise mechanism with printf-style formatting, chooseable severity, <code>WITH LOG / NOWAIT</code>. Does not honour XACT_ABORT and does not abort the batch by default."),
("Rethrow pattern","CATCH: roll back if needed, log, then bare <code>THROW;</code> so the caller sees the <i>original</i> error, number, and line."),
("XACT_STATE()","1 = open, committable transaction; -1 = open but <b>doomed</b> (only ROLLBACK allowed); 0 = no transaction."),
("SET XACT_ABORT ON","Makes (almost) any runtime error abort the batch and roll back the transaction automatically. The safety net for transactional procs."),
("Doomed transaction","A transaction that can no longer commit (XACT_STATE() = -1); any attempt to COMMIT or to write throws error 3930."),
("@@ERROR","Legacy: the previous statement's error number, reset by every statement. Pre-2005 code checks it after each statement — don't write new code this way."),
("sys.messages","Catalogue of error messages. <code>sp_addmessage</code> registers custom numbered messages RAISERROR can use.")],
["Severity ≤ 10 (PRINT-like warnings) never enters CATCH; severity ≥ 20 kills the connection before CATCH can run.",
"ERROR_* functions only have values inside a CATCH block (or a proc it calls) — read them immediately.",
"<code>THROW;</code> (bare, in CATCH) preserves the original error. Raising a NEW error loses the original — log it first.",
"Always terminate the statement <i>before</i> THROW with a semicolon; the parser can otherwise swallow THROW as a name.",
"In CATCH, check <code>@@TRANCOUNT</code> / <code>XACT_STATE()</code> and roll back before doing anything that writes.",
"<code>SET XACT_ABORT ON;</code> at the top of every proc that opens a transaction — Thursday's and Sunday's code depends on it."],
f'''
<h3>1. Life before TRY/CATCH: @@ERROR</h3>
{C(r"""
-- Legacy style you will still meet in old codebases: check after EVERY statement
UPDATE dbo.Employees SET Salary = Salary * 1.05 WHERE DepartmentId = 2;
IF @@ERROR <> 0
BEGIN
    PRINT 'Update failed';
    RETURN;
END
-- One statement later, @@ERROR has already been reset to 0 by the IF itself!
""", "legacy-error.sql", lang="sql")}
<p><code>@@ERROR</code> resets after every statement, so old procs are littered with <code>IF @@ERROR &lt;&gt; 0</code> checks — easy to forget one. Since SQL Server 2005, TRY/CATCH replaces all of it.</p>

<h3>2. TRY/CATCH basics</h3>
{C(r"""
BEGIN TRY
    DECLARE @perHead DECIMAL(10,2) = 180000 / 0;   -- divide by zero: error 8134, severity 16
    PRINT 'never reached';
END TRY
BEGIN CATCH
    PRINT 'Caught: ' + ERROR_MESSAGE();
END CATCH;
-- Caught: Divide by zero error encountered.
""", "try-catch.sql", lang="sql")}
<p>What CATCH does <b>not</b> catch:</p>
{ul(["Severity ≤ 10: informational messages (e.g. <code>RAISERROR(... , 10, 1)</code>) sail straight past CATCH.",
"Severity ≥ 20: the connection is terminated; nothing in this session runs after it.",
"Compile/binding errors in the <i>same scope</i> — e.g. referencing a missing table in this batch. An <b>outer</b> caller's CATCH does see them, which is one more reason application-facing logic belongs in procs.",
"KILL / client timeouts (attention events): the batch just stops; CATCH never runs. This is why Sunday's proc also sets XACT_ABORT ON."])}

<h3>3. The ERROR_* functions and an error log</h3>
{C(r"""
CREATE TABLE dbo.ErrorLog (
    ErrorLogId   INT IDENTITY PRIMARY KEY,
    LoggedAt     DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
    ErrorNumber  INT           NOT NULL,
    Severity     INT           NOT NULL,
    State        INT           NOT NULL,
    ProcName     NVARCHAR(128) NULL,
    ErrorLine    INT           NULL,
    Message      NVARCHAR(4000) NOT NULL,
    LoggedBy     SYSNAME       NOT NULL DEFAULT SUSER_SNAME()
);
GO
BEGIN TRY
    UPDATE dbo.Employees SET Salary = -1 WHERE EmployeeId = 2;   -- assume CHECK (Salary >= 0)
END TRY
BEGIN CATCH
    INSERT dbo.ErrorLog (ErrorNumber, Severity, State, ProcName, ErrorLine, Message)
    VALUES (ERROR_NUMBER(), ERROR_SEVERITY(), ERROR_STATE(),
            ERROR_PROCEDURE(), ERROR_LINE(), ERROR_MESSAGE());
    THROW;    -- logged, now rethrow so the caller still fails loudly
END CATCH;
""", "error-log.sql", lang="sql")}
{C(r"""
-- What the caller sees (example output):
Msg 547, Level 16, State 0, Line 13
The UPDATE statement conflicted with the CHECK constraint "CK_Employees_Salary". ...
""", lang="text")}
{warn("Logging the error and then swallowing it (<code>-- THROW</code> commented out) is how systems end up \"succeeding\" with half the data missing. Log <i>and</i> rethrow unless this layer can genuinely recover.", "Avoid")}

<h3>4. THROW vs RAISERROR</h3>
{C(r"""
-- THROW: number >= 50000, message, state. Severity is ALWAYS 16; batch always terminates.
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WHERE EmployeeId = 42)
    THROW 50001, N'Employee 42 does not exist.', 1;

-- RAISERROR: printf formatting, chooseable severity, more options
RAISERROR (N'Employee %d does not exist in department %s.', 16, 1, 42, N'Finance');
RAISERROR (N'Heads-up: nightly job started', 10, 1) WITH NOWAIT;  -- info msg, prints immediately
""", "throw-vs-raiserror.sql", lang="sql")}
{table(["","THROW (2012+)","RAISERROR"],[
["Severity","Always 16","You choose (0–19; higher needs sysadmin + WITH LOG)"],
["Message formatting","Plain string (use FORMATMESSAGE to compose)","printf-style %s, %d in the call"],
["sys.messages integration","No (ad-hoc number ≥ 50000)","Yes — message ids via sp_addmessage"],
["Rethrow original error","<code>THROW;</code> — perfect rethrow","Cannot; must fake it from ERROR_* values"],
["Terminates the batch","Always","No (unless severity ≥ 20 or WITH LOG scenarios)"],
["Honours XACT_ABORT","Yes","No"],
["Recommendation","Default choice for new code","Formatting, custom message catalogue, progress messages (NOWAIT)"]])}
{tip("Need a formatted message with THROW? <code>DECLARE @msg NVARCHAR(2048) = FORMATMESSAGE(N'Employee %d not found', @id); THROW 50001, @msg, 1;</code>")}

<h3>5. The rethrow pattern</h3>
{C(r"""
CREATE OR ALTER PROCEDURE dbo.usp_GiveRaiseSafe
    @EmployeeId INT,
    @Percent    DECIMAL(5,2)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @Percent NOT BETWEEN 0 AND 50
        THROW 50002, N'@Percent must be between 0 and 50.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Employees
        SET Salary = Salary * (1 + @Percent / 100.0)
        WHERE EmployeeId = @EmployeeId;

        IF @@ROWCOUNT = 0
            THROW 50003, N'Employee does not exist.', 1;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;   -- clean up OUR transaction...

        -- (optionally log to dbo.ErrorLog here)

        THROW;                                     -- ...then rethrow the ORIGINAL error
    END CATCH;
END
""", "rethrow-pattern.sql", lang="sql")}
<p>Why bare <code>THROW;</code>? The caller gets the original number, message and line — exactly like C#'s <code>throw;</code> vs <code>throw ex;</code> from Week 3. Raising a fresh error instead would be T-SQL's <code>throw ex</code>: context lost.</p>
{warn("Write <code>ROLLBACK TRANSACTION;</code> with the semicolon. Without it, <code>ROLLBACK TRANSACTION THROW</code> parses THROW as a transaction name and your rethrow never happens — a famous, real-world bug.", "Gotcha")}

<h3>6. XACT_ABORT and XACT_STATE</h3>
{C(r"""
-- XACT_STATE() answers: "can I still commit?"
--   1  = open transaction, committable
--   0  = no transaction
--  -1  = open but DOOMED: only ROLLBACK is allowed
BEGIN CATCH
    IF XACT_STATE() = -1
        ROLLBACK TRANSACTION;          -- doomed: the only legal move
    ELSE IF XACT_STATE() = 1
        ROLLBACK TRANSACTION;          -- our policy: a caught error voids the whole unit
    THROW;
END CATCH;
""", "xact-state.sql", lang="sql")}
{ul(["<b>SET XACT_ABORT ON</b> turns most runtime errors into \"doom the transaction and abort the batch\". With it, a client timeout mid-transaction rolls back instead of leaving locks held by an open, orphaned transaction.",
"With XACT_ABORT ON inside TRY, control still reaches CATCH — but the transaction is usually doomed (XACT_STATE() = -1), so roll back before any further writes.",
"Microsoft's own guidance for procs that modify data: <code>SET NOCOUNT ON; SET XACT_ABORT ON;</code> as the opening lines. That's the house style for the rest of this course."])}
''',
["Relying on @@ERROR two statements after the failure (it's already reset).",
"Expecting CATCH to see severity-10 RAISERROR messages or severity-20+ fatal errors.",
"Raising a brand-new generic error in CATCH instead of logging and rethrowing with <code>THROW;</code>.",
"Missing semicolon before THROW (especially after ROLLBACK TRANSACTION).",
"COMMITting in CATCH when XACT_STATE() is -1 — error 3930, the transaction was doomed."],
("40 min", ["Write a script that inserts two employees inside TRY, where the second violates the UNIQUE email constraint. In CATCH, log to <code>dbo.ErrorLog</code> and rethrow. Verify the log row and that the caller still sees error 2627.",
"Rewrite Monday's <code>usp_GiveRaise</code> to THROW 50002/50003 errors instead of RETURN codes. Which call sites get simpler?",
"Experiment: run <code>RAISERROR(N'x', 10, 1)</code> and <code>RAISERROR(N'x', 16, 1)</code> inside TRY and note which reaches CATCH. Then THROW from inside CATCH without a preceding semicolon after ROLLBACK TRANSACTION and observe the parse behaviour."]),
[("What three values can XACT_STATE() return and what do they mean?","1: an open transaction that can still commit. 0: no open transaction. -1: an open but doomed transaction — you can only roll it back; COMMIT throws error 3930."),
("Why is bare THROW; in CATCH better than raising a new error?","It rethrows the original error with its number, severity, state, message and line, so the caller (and your logs) see where it really happened — the T-SQL equivalent of C#'s <code>throw;</code> preserving the stack trace."),
("What does SET XACT_ABORT ON change?","Most runtime errors (and client timeouts/attentions) automatically doom and roll back the open transaction and abort the batch, instead of possibly continuing with the transaction still open. It's the standard safety net for data-modifying procs.")],
[("Basic","How does TRY/CATCH work in T-SQL and what can't it catch?","Errors with severity 11–19 inside TRY transfer control to CATCH. It cannot catch: severity ≤ 10 messages, severity ≥ 20 errors that kill the connection, compile/name-resolution errors raised in the same scope (an outer scope's CATCH can see those), or attention events like KILL and client timeouts."),
("Basic","Which functions give you error details in a CATCH block?","ERROR_NUMBER, ERROR_MESSAGE, ERROR_SEVERITY, ERROR_STATE, ERROR_LINE and ERROR_PROCEDURE. They keep their values anywhere inside the CATCH block (including procs called from it), unlike @@ERROR which resets after every statement."),
("Basic","THROW vs RAISERROR — key differences?","THROW (2012+) is the modern choice: always severity 16, always terminates the batch, honours XACT_ABORT, and bare THROW rethrows the original error. RAISERROR offers printf formatting, selectable severity, sys.messages integration and WITH NOWAIT, but can't rethrow and doesn't trigger XACT_ABORT behaviour."),
("Intermediate","Describe a robust CATCH block for a proc that writes data.","Check @@TRANCOUNT/XACT_STATE and roll back if a transaction is open (mandatory when XACT_STATE() = -1), optionally write a log record after the rollback, then rethrow with bare THROW so callers aren't fooled into thinking the operation succeeded."),
("Intermediate","What is a doomed transaction and how do you end up with one?","A transaction in XACT_STATE() = -1: still open (holding locks) but unable to commit. You typically get one when an error occurs with SET XACT_ABORT ON, or certain severe errors inside TRY. Any work attempted before ROLLBACK fails with error 3930."),
("Intermediate","Why do teams set XACT_ABORT ON even though TRY/CATCH exists?","TRY/CATCH never runs for attention events — a client timeout mid-transaction leaves the transaction open and its locks held, blocking everyone. XACT_ABORT ON rolls back automatically in exactly those cases, so the two mechanisms cover each other.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Transactions, @@TRANCOUNT, savepoints and isolation levels",
"Group statements into all-or-nothing transactions, understand why \"nested transactions\" are a myth, and reason about the five isolation levels through the three classic anomalies.",
[("Transaction","A unit of work that either fully commits or fully rolls back — never half-applies."),
("ACID","Atomicity (all or nothing), Consistency (constraints hold before and after), Isolation (concurrent transactions don't trample each other), Durability (committed = survives a crash, via the write-ahead log)."),
("Autocommit","SQL Server's default: every single statement is its own transaction. An UPDATE hitting 10,000 rows is still atomic on its own."),
("Explicit transaction","<code>BEGIN TRANSACTION … COMMIT / ROLLBACK</code>: you decide the unit of work."),
("@@TRANCOUNT","Current transaction nesting depth. BEGIN TRAN adds 1; COMMIT subtracts 1 (only the last one really commits); ROLLBACK zeroes it."),
("Nested transactions","A myth: inner BEGIN TRAN/COMMIT pairs only move the counter. There is exactly one real transaction — the outermost."),
("Savepoint","<code>SAVE TRANSACTION name</code>: a marker you can roll back <i>to</i> without abandoning the whole transaction."),
("Isolation level","How much a transaction is protected from others' concurrent changes; a trade between correctness and concurrency."),
("Dirty read","Reading data another transaction has modified but not yet committed — it may be rolled back and have \"never happened\"."),
("Non-repeatable read","Reading the same row twice in one transaction and getting different values, because someone committed an update in between."),
("Phantom read","Re-running the same range query and seeing <i>new rows</i>, because someone committed an insert matching your WHERE clause."),
("READ COMMITTED","The default: no dirty reads; readers take shared locks briefly (or read versions under RCSI)."),
("SNAPSHOT isolation","Transaction sees a consistent version of the data as of its start, via row versions in tempdb; writers don't block readers. Update conflicts raise error 3960."),
("RCSI","READ_COMMITTED_SNAPSHOT: READ COMMITTED semantics, but each <i>statement</i> reads the latest committed version instead of waiting on locks. Default on Azure SQL Database."),
("Version store","The area in tempdb that keeps old row versions for SNAPSHOT/RCSI readers.")],
["Autocommit already makes each statement atomic; explicit transactions are for <b>multi-statement</b> invariants (debit + credit, order + lines + stock).",
"COMMIT when @@TRANCOUNT &gt; 1 commits nothing — it just decrements the counter. Only the outermost COMMIT writes.",
"ROLLBACK anywhere rolls back <b>everything</b> and sets @@TRANCOUNT to 0 — exiting a proc with a different @@TRANCOUNT than it entered with raises error 266.",
"Never wait for user/application input while a transaction is open: you're holding locks.",
"Anomaly ladder: READ UNCOMMITTED allows dirty + non-repeatable + phantom; READ COMMITTED blocks dirty; REPEATABLE READ also blocks non-repeatable; SERIALIZABLE blocks all three.",
"SNAPSHOT/RCSI take a different route: versions instead of reader locks — readers never block writers and vice versa."],
f'''
<h3>1. BEGIN / COMMIT / ROLLBACK and ACID</h3>
<p>A bonus payout must update the salary <i>and</i> write the ledger row. One without the other is corruption:</p>
{C(r"""
CREATE TABLE dbo.BonusLedger (
    LedgerId   INT IDENTITY PRIMARY KEY,
    EmployeeId INT NOT NULL REFERENCES dbo.Employees (EmployeeId),
    Amount     DECIMAL(10,2) NOT NULL CHECK (Amount > 0),
    PaidAt     DATETIME2(0) NOT NULL DEFAULT SYSDATETIME()
);
GO
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE dbo.Employees
    SET Salary = Salary + 2000
    WHERE EmployeeId = 2;

    INSERT dbo.BonusLedger (EmployeeId, Amount)
    VALUES (2, 2000);

    COMMIT TRANSACTION;          -- both changes become durable together
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;   -- neither change survives
    THROW;
END CATCH;
""", "bonus-transaction.sql", lang="sql")}
{table(["Property","In this example"],[
["Atomicity","Salary update and ledger insert commit or vanish together"],
["Consistency","CHECK (Amount &gt; 0) and the FK hold before and after; a violating transaction rolls back"],
["Isolation","Another session summing BonusLedger never sees the insert without the salary update"],
["Durability","After COMMIT returns, the change is in the transaction log — a power cut won't lose it"]])}

<h3>2. @@TRANCOUNT and the nested-transaction myth</h3>
{C(r"""
SELECT @@TRANCOUNT AS tc;      -- 0
BEGIN TRANSACTION;
SELECT @@TRANCOUNT AS tc;      -- 1
    BEGIN TRANSACTION;         -- "nested"... but no new transaction starts
    SELECT @@TRANCOUNT AS tc;  -- 2
    COMMIT;                    -- commits NOTHING — just decrements the counter
    SELECT @@TRANCOUNT AS tc;  -- 1
ROLLBACK;                      -- rolls back EVERYTHING since the first BEGIN TRAN
SELECT @@TRANCOUNT AS tc;      -- 0
""", "trancount.sql", lang="sql")}
<p>There is only ever one real transaction. Inner COMMITs are bookkeeping; any ROLLBACK (at any depth) undoes the lot. This bites when a proc that opens its own transaction is called from inside a caller's transaction:</p>
{C(r"""
-- A proc that works standalone AND inside a caller's transaction
CREATE OR ALTER PROCEDURE dbo.usp_PayBonus
    @EmployeeId INT, @Amount DECIMAL(10,2)
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    DECLARE @startedHere BIT = 0;

    BEGIN TRY
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRANSACTION;          -- only open one if nobody did yet
            SET @startedHere = 1;
        END

        UPDATE dbo.Employees SET Salary = Salary + @Amount WHERE EmployeeId = @EmployeeId;
        IF @@ROWCOUNT = 0 THROW 50010, N'Employee does not exist.', 1;
        INSERT dbo.BonusLedger (EmployeeId, Amount) VALUES (@EmployeeId, @Amount);

        IF @startedHere = 1 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @startedHere = 1 AND @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;      -- if the caller owns the transaction, the caller decides to roll back
    END CATCH;
END
""", "proc-in-transaction.sql", lang="sql")}
{warn("A proc must leave @@TRANCOUNT exactly as it found it, or SQL Server raises error 266 (\"Transaction count after EXECUTE indicates a mismatching number of BEGIN and COMMIT statements\"). The @startedHere pattern above guarantees that.", "Rule")}

<h3>3. Savepoints</h3>
{C(r"""
BEGIN TRANSACTION;

INSERT dbo.BonusLedger (EmployeeId, Amount) VALUES (2, 1000);   -- must succeed

SAVE TRANSACTION OptionalPart;                                   -- marker

BEGIN TRY
    INSERT dbo.BonusLedger (EmployeeId, Amount) VALUES (4, 500); -- nice-to-have
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION OptionalPart;   -- undo ONLY the optional part
END CATCH;                                -- @@TRANCOUNT is still 1 here

COMMIT TRANSACTION;                       -- the first insert (and the second, if it worked) commit
""", "savepoint.sql", lang="sql")}
<p><code>ROLLBACK TRANSACTION savepoint_name</code> does <b>not</b> decrement @@TRANCOUNT — the transaction stays open. Savepoints are rare in practice (usually you want all-or-nothing), but they shine for \"mandatory core + optional extras\" units.</p>

<h3>4. Isolation levels and the three anomalies</h3>
{C(r"""
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;   -- per session, until changed
-- READ UNCOMMITTED | READ COMMITTED | REPEATABLE READ | SERIALIZABLE | SNAPSHOT
""", lang="sql")}
{table(["Level","Dirty read","Non-repeatable read","Phantom","How it's achieved"],[
["READ UNCOMMITTED","Possible","Possible","Possible","Readers take no shared locks (≈ NOLOCK everywhere)"],
["READ COMMITTED (default)","No","Possible","Possible","Shared locks held only while reading each row"],
["REPEATABLE READ","No","No","Possible","Shared locks kept until COMMIT on rows read"],
["SERIALIZABLE","No","No","No","Key-range locks: nobody may insert into scanned ranges"],
["SNAPSHOT","No","No","No*","Row versions as of transaction start; writers raise 3960 on conflict"]])}
<p class="muted">* SNAPSHOT shows you a frozen, consistent picture — no phantoms <i>within your snapshot</i>; the rows may have changed since. Locks stack concurrency costs; versions stack tempdb costs.</p>

<h3>5. Seeing the anomalies with two sessions</h3>
<p>Open two query windows (Session A, Session B) and run the numbered steps in order.</p>
<h4>Dirty read (READ UNCOMMITTED)</h4>
{C(r"""
-- Session A, step 1: update but DON'T commit
BEGIN TRANSACTION;
UPDATE dbo.Employees SET Salary = 999999 WHERE EmployeeId = 2;

-- Session B, step 2: dirty-read it
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT Salary FROM dbo.Employees WHERE EmployeeId = 2;   -- 999999.00  <- a value that
                                                          --   was never committed!
-- Session A, step 3:
ROLLBACK;   -- the 999999 "never happened" — Session B reported fiction
""", "dirty-read.sql", lang="sql")}
<h4>Non-repeatable read (fixed by REPEATABLE READ)</h4>
{C(r"""
-- Session A, step 1:
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN TRANSACTION;
SELECT Salary FROM dbo.Employees WHERE EmployeeId = 2;   -- 72500.00

-- Session B, step 2 (autocommit):
UPDATE dbo.Employees SET Salary = 80000 WHERE EmployeeId = 2;   -- commits immediately

-- Session A, step 3: same query, same transaction...
SELECT Salary FROM dbo.Employees WHERE EmployeeId = 2;   -- 80000.00  <- changed mid-transaction
COMMIT;
-- Re-run with SET TRANSACTION ISOLATION LEVEL REPEATABLE READ in Session A:
-- step 2 now BLOCKS until Session A commits -> both reads agree.
""", "non-repeatable.sql", lang="sql")}
<h4>Phantom read (fixed by SERIALIZABLE)</h4>
{C(r"""
-- Session A, step 1:
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN TRANSACTION;
SELECT COUNT(*) FROM dbo.Employees WHERE DepartmentId = 2;   -- 3

-- Session B, step 2: INSERT a new department-2 employee (commits fine:
-- REPEATABLE READ only locks rows that were read, not the "gap")
INSERT dbo.Employees (FirstName, LastName, Email, DepartmentId, Salary, HireDate)
VALUES (N'Arjun', N'Nair', N'arjun.nair@lnw-demo.in', 2, 54000, '2026-11-01');

-- Session A, step 3:
SELECT COUNT(*) FROM dbo.Employees WHERE DepartmentId = 2;   -- 4: a phantom appeared
COMMIT;
-- Under SERIALIZABLE, step 2 blocks: key-range locks protect the whole predicate.
""", "phantom.sql", lang="sql")}

<h3>6. SNAPSHOT and READ_COMMITTED_SNAPSHOT (RCSI)</h3>
{C(r"""
ALTER DATABASE HR SET ALLOW_SNAPSHOT_ISOLATION ON;    -- enables SNAPSHOT on request
ALTER DATABASE HR SET READ_COMMITTED_SNAPSHOT ON      -- changes what READ COMMITTED means
    WITH ROLLBACK IMMEDIATE;                          -- (kicks out open transactions)
GO
-- SNAPSHOT: a frozen, consistent view as of transaction start
SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
BEGIN TRANSACTION;
SELECT SUM(Salary) FROM dbo.Employees;    -- consistent total, even while others update
-- ... other sessions commit changes; you keep seeing your snapshot ...
COMMIT;
""", "snapshot.sql", lang="sql")}
{table(["","SNAPSHOT","RCSI (READ_COMMITTED_SNAPSHOT)"],[
["Consistent as of","Transaction start","Each statement's start"],
["Opt in per transaction?","Yes — SET TRANSACTION ISOLATION LEVEL SNAPSHOT","No — silently redefines READ COMMITTED for everyone"],
["Readers block writers?","No","No"],
["Write-write conflicts","Error 3960 (\"snapshot isolation transaction aborted due to update conflict\") — retry","Normal blocking rules"],
["Cost","tempdb version store, longer version retention","tempdb version store"],
["Where it's the default","—","Azure SQL Database"]])}
{tip("RCSI is the pragmatic favourite for OLTP read workloads: readers stop blocking writers with zero code changes. Just watch tempdb, and remember queries that must see the very latest committed-and-locked truth (like Sunday's stock check) still need UPDLOCK hints.")}
''',
["Opening a transaction and then doing slow work (calls, user input) while holding locks.",
"Believing an inner COMMIT saved anything — only the outermost COMMIT writes.",
"Procs that BEGIN TRAN unconditionally and ROLLBACK on error, breaking callers' transactions (error 266).",
"Using NOLOCK/READ UNCOMMITTED on financial or stock queries and shipping dirty reads to users.",
"Turning on SERIALIZABLE \"to be safe\" everywhere and wondering where the throughput went."],
("40 min", ["Write the bonus-payout transaction, then force the ledger INSERT to fail (violate its CHECK). Prove the salary update rolled back too.",
"Reproduce the dirty read and the non-repeatable read with two query windows, then fix each by raising Session A's (or B's) isolation level. Note exactly which step starts blocking.",
"Call <code>dbo.usp_PayBonus</code> standalone, then from inside an explicit transaction that you ROLLBACK afterwards. Verify @@TRANCOUNT behaves and the ledger row disappears in case two."]),
[("Why are nested transactions \"a myth\" in SQL Server?","BEGIN TRAN inside a transaction only increments @@TRANCOUNT; inner COMMITs just decrement it. There's one real transaction — the outermost — and any ROLLBACK undoes all of it and zeroes the counter."),
("Which anomaly does each isolation level eliminate?","READ COMMITTED stops dirty reads; REPEATABLE READ additionally stops non-repeatable reads; SERIALIZABLE additionally stops phantoms (key-range locks); SNAPSHOT gives a consistent versioned view with none of the three, trading locks for tempdb versions and possible 3960 update conflicts."),
("What's the difference between SNAPSHOT and RCSI?","SNAPSHOT freezes the view at transaction start and must be requested per transaction; write conflicts abort with 3960. RCSI redefines READ COMMITTED database-wide so each statement sees the latest committed version — no code changes, statement-level consistency only.")],
[("Basic","Explain ACID with a concrete example.","Atomicity: order + order lines + stock decrement commit or roll back together. Consistency: constraints (stock ≥ 0, FKs) hold after commit. Isolation: a concurrent report never sees the order without its lines. Durability: once COMMIT returns, the write-ahead log guarantees the data survives a crash."),
("Basic","What happens to @@TRANCOUNT on BEGIN, COMMIT and ROLLBACK?","BEGIN TRANSACTION increments it. COMMIT decrements it, and only the COMMIT that takes it from 1 to 0 makes changes permanent. ROLLBACK (without a savepoint name) rolls back everything and sets it straight to 0, whatever the depth."),
("Basic","What is a dirty read and which level permits it?","Reading uncommitted changes of another transaction — data that may be rolled back. Only READ UNCOMMITTED (or the NOLOCK hint, which is the same thing per table) permits it; every other level prevents it."),
("Intermediate","How does a proc safely manage transactions when it might be called inside an existing one?","Check @@TRANCOUNT at entry: if 0, begin and later commit your own transaction; if already &gt; 0, join it — do your work without BEGIN/COMMIT and on error just rethrow and let the owner roll back. Either way the proc must exit with the same @@TRANCOUNT it entered with or error 266 fires."),
("Intermediate","What do savepoints do, and what don't they do?","SAVE TRANSACTION name marks a point you can ROLLBACK TRANSACTION name back to, undoing only the work after the mark while keeping the transaction open (@@TRANCOUNT unchanged). They don't commit anything, don't release most locks, and can't survive a full ROLLBACK."),
("Advanced","A reporting query blocks OLTP writers. Compare the fixes.","NOLOCK: quick but wrong — dirty reads, double/missing rows on page splits. RCSI: readers use row versions, writers unblocked, statement-level consistency, tempdb overhead — usually the right default. SNAPSHOT: full transaction-consistent reporting at the cost of version retention and 3960 retry logic for writers in the same transaction. Offloading to a readable replica removes the contention entirely but adds latency and infrastructure.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Locking, blocking, deadlocks — and triggers",
"See which locks SQL Server takes and how to find who's blocking whom; understand, provoke and retry deadlocks; and write set-based triggers while knowing why business logic rarely belongs in them.",
[("Lock","An in-memory marker that gives a session rights over a resource (row, page, table) and makes others wait for incompatible access."),
("Shared lock (S)","Taken to read. Compatible with other S locks; blocks X."),
("Exclusive lock (X)","Taken to modify. Compatible with nothing — one writer at a time per resource."),
("Update lock (U)","\"Intending to write\": taken while locating rows to update. Compatible with S, not with other U — which prevents a classic deadlock between two updaters."),
("Intent lock (IS/IX)","Placed on the page and table to advertise row-level locks below, so a table-level request can be checked without scanning every row lock."),
("Granularity","The size of the locked resource: KEY (row in an index), RID (heap row), PAGE, HOBT/TABLE. Finer = more concurrency, more overhead."),
("Lock escalation","When one statement holds ~5,000 locks on an object, SQL Server trades them for a single table lock — cheaper, but suddenly everyone waits."),
("Blocking","Normal lock waiting: session B needs a lock session A holds. Resolves itself when A commits — unless A is idle holding a transaction open."),
("Deadlock","A cycle: A holds what B wants and B holds what A wants. Nobody can ever proceed, so SQL Server kills one."),
("Deadlock victim","The transaction SQL Server chooses to kill (usually the cheapest to roll back) — it gets error 1205 and should be retried."),
("Deadlock graph","An XML/visual report of the cycle: which sessions, which resources, which statements. Captured automatically by the system_health session."),
("Trigger","T-SQL attached to a table that runs automatically on INSERT/UPDATE/DELETE — AFTER (post-check) or INSTEAD OF (replaces the action)."),
("inserted / deleted","Virtual tables inside a trigger: the new row versions and the old ones. An UPDATE populates both."),
("UPDATE(col)","Trigger function: true when the column appeared in the SET/insert list (even if set to the same value)."),
("sp_whoisactive","A free, widely used community proc (Adam Machanic) that shows running sessions, blockers and wait info far more readably than sp_who2.")],
["Readers block writers and writers block readers (under plain READ COMMITTED) — but readers never block readers.",
"Blocking is normal and brief; a problem only when transactions are long or idle-but-open. Deadlocks are always a bug-shaped smell.",
"SQL Server detects deadlocks in seconds, kills the cheapest victim with error 1205 — the fix is to retry, and to stop the cycle forming.",
"Cycle prevention rule #1: every transaction touches shared tables in the <b>same order</b>.",
"Triggers fire <b>once per statement</b>, not per row — always join <code>inserted</code>/<code>deleted</code> as sets.",
"Keep triggers for auditing and denormalised bookkeeping; put business rules in procs/services where they're visible and testable."],
f'''
<h3>1. Lock modes and granularity (awareness level)</h3>
{table(["Mode","Meaning","Typical taker"],[
["S (Shared)","Reading; others may also read","SELECT under READ COMMITTED"],
["U (Update)","Scanning for rows to change","UPDATE while locating rows"],
["X (Exclusive)","Changing data","INSERT / UPDATE / DELETE"],
["IS / IX (Intent)","\"Rows below me hold S/X\"","Placed on page+table above row locks"],
["Sch-S / Sch-M","Schema stability / modification","Queries / ALTER TABLE"],
["Key-range","Locks a range in an index, including gaps","SERIALIZABLE scans"]])}
<p>Granularity: SQL Server usually locks at the <b>row</b> (KEY/RID) level, advertising upward with intent locks. Hold ~5,000+ locks from one statement on one table and it <b>escalates</b> to a full table lock — great for memory, terrible for whoever else needed that table. Mass updates in batches of a few thousand rows avoid it.</p>

<h3>2. Watching blocking happen</h3>
{C(r"""
-- Session A: take a lock and sit on it (simulating a long transaction)
BEGIN TRANSACTION;
UPDATE dbo.Employees SET Salary = Salary + 1 WHERE EmployeeId = 2;
-- (no COMMIT yet)

-- Session B: now blocks...
UPDATE dbo.Employees SET City = N'Pune' WHERE EmployeeId = 2;   -- waits forever
""", "blocking-demo.sql", lang="sql")}
{C(r"""
-- Session C: who is blocking whom?
SELECT r.session_id, r.blocking_session_id, r.wait_type, r.wait_time, r.command,
       t.text AS running_sql
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.blocking_session_id <> 0;

-- What locks does the blocker hold?
SELECT request_session_id AS spid, resource_type, request_mode, request_status,
       OBJECT_NAME(p.object_id) AS table_name
FROM sys.dm_tran_locks l
LEFT JOIN sys.partitions p ON p.hobt_id = l.resource_associated_entity_id
WHERE l.resource_database_id = DB_ID();
""", "find-blocking.sql", lang="sql")}
{C(r"""
-- Example output of the first query
session_id  blocking_session_id  wait_type  wait_time  command  running_sql
----------- -------------------- ---------- ---------- -------- -------------------------
63          58                   LCK_M_X    41238      UPDATE   UPDATE dbo.Employees ...
""", lang="text")}
{tip("Install <code>sp_whoisactive</code> (free, whoisactive.com) on every dev server: <code>EXEC sp_whoisactive;</code> shows blockers, waits, and the exact statements in one readable grid. <code>SET LOCK_TIMEOUT 5000;</code> makes your own session give up with error 1222 instead of waiting forever.")}

<h3>3. Deadlocks: making one on purpose</h3>
{C(r"""
-- Session A                                 | -- Session B
BEGIN TRANSACTION;                           | BEGIN TRANSACTION;
UPDATE dbo.Employees                         | UPDATE dbo.Departments
SET Salary += 1 WHERE EmployeeId = 2;        | SET Name = Name WHERE DepartmentId = 2;
                                             |
-- step 3: now wants Departments...          | -- step 4: now wants Employees...
UPDATE dbo.Departments                       | UPDATE dbo.Employees
SET Name = Name WHERE DepartmentId = 2;      | SET Salary += 1 WHERE EmployeeId = 2;
-- (blocks on B's X lock)                    | -- (blocks on A's X lock) => CYCLE
""", "deadlock-demo.sql", lang="sql")}
{C(r"""
-- Within ~5 seconds, one session (the victim) gets:
Msg 1205, Level 13, State 51, Line 6
Transaction (Process ID 63) was deadlocked on lock resources with another process
and has been chosen as the deadlock victim. Rerun the transaction.
""", lang="text")}
<p>The other session's work proceeds untouched. The victim's transaction is rolled back entirely — \"Rerun the transaction\" is literal advice, which is why real systems wrap such calls in retry logic.</p>
{C(r"""
-- Read recent deadlock graphs from the always-on system_health session
SELECT xed.query('.') AS DeadlockGraph
FROM (SELECT CAST(st.target_data AS XML) AS td
      FROM sys.dm_xe_session_targets st
      JOIN sys.dm_xe_sessions s ON s.address = st.event_session_address
      WHERE s.name = N'system_health' AND st.target_name = N'ring_buffer') AS src
CROSS APPLY td.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS x(xed);
-- In SSMS: Management > Extended Events > system_health > watch the
-- xml_deadlock_report events, or open the XML as a visual graph.
""", "deadlock-graph.sql", lang="sql")}

<h3>4. Preventing and surviving deadlocks</h3>
{ul(["<b>Order resources consistently.</b> If every transaction updates Employees before Departments, the A-waits-B-waits-A cycle cannot form. Agree an order (e.g. parent then child, or alphabetical) and enforce it in code review.",
"<b>Keep transactions short.</b> Do reads, calculations and validations first; open the transaction for the writes only.",
"<b>Index your WHERE clauses and foreign keys.</b> A missing index turns a 1-row update into a scan that locks everything it touches.",
"<b>Take the strongest lock first.</b> Sunday's stock check reads with <code>UPDLOCK</code> precisely so check-then-update can't deadlock with a twin.",
"<b>Retry the victim.</b> Error 1205 is transient by design; 2–3 retries with a tiny delay absorb almost all of them."])}
{C(r"""
-- Retry skeleton (Sunday's project ships a full version)
DECLARE @attempts INT = 0;
retry:
BEGIN TRY
    SET @attempts += 1;
    EXEC dbo.usp_PayBonus @EmployeeId = 2, @Amount = 500;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() = 1205 AND @attempts < 3
    BEGIN
        WAITFOR DELAY '00:00:00.200';   -- small backoff
        GOTO retry;
    END;
    THROW;
END CATCH;
""", "retry-skeleton.sql", lang="sql")}

<h3>5. AFTER triggers and the inserted/deleted tables</h3>
{C(r"""
CREATE TABLE dbo.SalaryAudit (
    AuditId    INT IDENTITY PRIMARY KEY,
    EmployeeId INT            NOT NULL,
    OldSalary  DECIMAL(10,2)  NOT NULL,
    NewSalary  DECIMAL(10,2)  NOT NULL,
    ChangedBy  SYSNAME        NOT NULL DEFAULT SUSER_SNAME(),
    ChangedAt  DATETIME2(0)   NOT NULL DEFAULT SYSDATETIME()
);
GO
CREATE OR ALTER TRIGGER dbo.trg_Employees_AuditSalary
ON dbo.Employees
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT UPDATE(Salary) RETURN;        -- Salary wasn't in the SET list at all

    INSERT dbo.SalaryAudit (EmployeeId, OldSalary, NewSalary)
    SELECT i.EmployeeId, d.Salary, i.Salary
    FROM inserted i                       -- new versions of the updated rows
    JOIN deleted  d ON d.EmployeeId = i.EmployeeId   -- old versions
    WHERE i.Salary <> d.Salary;           -- only genuine changes
END
GO
-- One statement, three rows, ONE trigger firing, three audit rows:
UPDATE dbo.Employees SET Salary = Salary * 1.10 WHERE DepartmentId = 2;
SELECT EmployeeId, OldSalary, NewSalary FROM dbo.SalaryAudit;
""", "audit-trigger.sql", lang="sql")}
{C(r"""
EmployeeId  OldSalary    NewSalary
----------- ------------ ------------
2           72500.00     79750.00
4           58000.00     63800.00
9           66000.00     72600.00
""", lang="text")}
{warn("The #1 trigger bug: assuming one row. <code>SELECT @id = EmployeeId FROM inserted</code> silently picks ONE row of a multi-row update and ignores the rest. Triggers fire per statement — always write set-based joins against inserted/deleted.", "Gotcha")}

<h3>6. INSTEAD OF triggers — and why business logic avoids triggers</h3>
{C(r"""
-- Soft delete: turn DELETE into "deactivate"
CREATE OR ALTER TRIGGER dbo.trg_Employees_SoftDelete
ON dbo.Employees
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE e
    SET e.IsActive = 0
    FROM dbo.Employees e
    JOIN deleted d ON d.EmployeeId = e.EmployeeId;   -- the DELETE itself never happens
END
GO
DELETE dbo.Employees WHERE EmployeeId = 4;
SELECT EmployeeId, IsActive FROM dbo.Employees WHERE EmployeeId = 4;  -- 4 | 0 (still there)
""", "instead-of.sql", lang="sql")}
<p>INSTEAD OF triggers also make non-updatable views updatable (route the write to the base tables). But hold the line on scope:</p>
{table(["Triggers are good for","Business logic in triggers goes wrong because"],[
["Audit trails (who changed what, when)","Invisible: an UPDATE quietly does five other things nobody sees at the call site"],
["Denormalised counters/totals kept in sync","Hard to test: no way to call the logic without touching the table"],
["Enforcing invariants no constraint can express","Per-statement surprises: multi-row bugs like the one above"],
["Soft-delete routing","Performance: every write pays the trigger tax, and triggers can fire triggers (nested)"],
["","Ordering: with multiple triggers only first/last is settable (sp_settriggerorder)"]])}
{tip("Rule of thumb: a trigger may <i>record</i> or <i>protect</i>, never <i>decide</i>. Order totals, stock checks and pricing live in Sunday's stored procedure, not in a trigger.")}
''',
["Leaving a transaction open while idle (\"I'll commit after lunch\") — the whole table queues up behind you.",
"Sprinkling NOLOCK to \"fix\" blocking instead of shortening transactions or enabling RCSI.",
"Treating error 1205 as fatal instead of retrying the transaction.",
"Single-row assumptions in triggers (variables assigned from inserted).",
"Putting cascading business updates in triggers, then spending a week finding out why stock goes negative \"on its own\"."],
("40 min", ["Create the blocking demo, find the blocker with <code>sys.dm_exec_requests</code>, then kill or commit it. Repeat with <code>SET LOCK_TIMEOUT 2000</code> in the blocked session and observe error 1222.",
"Produce the deadlock with two windows, note which session was chosen as victim, and pull the deadlock graph out of system_health. Then fix the scripts by making both sessions update tables in the same order — confirm the deadlock is gone.",
"Extend <code>trg_Employees_AuditSalary</code> to also audit INSERTs (AFTER INSERT, OldSalary = new salary or 0 — your design call). Verify with a 3-row INSERT that one statement produces three audit rows."]),
[("What's the difference between blocking and a deadlock?","Blocking is one-directional waiting that resolves when the blocker commits. A deadlock is a cycle of waits that can never resolve, so SQL Server detects it and kills one participant (error 1205). Blocking is normal; deadlocks indicate conflicting access patterns."),
("Why does consistent resource ordering prevent deadlocks?","A deadlock needs a cycle: A holds X and wants Y while B holds Y and wants X. If every transaction acquires X before Y, whoever gets X first wins and the other simply waits — a queue, not a cycle."),
("What are inserted and deleted inside a trigger?","Virtual tables scoped to the trigger: inserted holds the new row versions (INSERT/UPDATE), deleted holds the old ones (DELETE/UPDATE). They can hold 0, 1 or many rows because triggers fire once per statement.")],
[("Basic","Name the main lock modes and their compatibility.","Shared (S) for reads — compatible with other S. Exclusive (X) for writes — compatible with nothing. Update (U) while locating rows to change — compatible with S but not another U, which stops two updaters deadlocking during their scans. Intent locks (IS/IX) mark the page/table so higher-level requests can be resolved quickly."),
("Basic","How do you find what's blocking a query right now?","sys.dm_exec_requests shows waiting sessions with blocking_session_id; join sys.dm_exec_sql_text for the statements. sys.dm_tran_locks lists held/waiting locks. In practice most DBAs run sp_whoisactive, which presents all of this in one call."),
("Basic","What is lock escalation?","When one statement accumulates roughly 5,000 locks on a table, SQL Server replaces the row/page locks with a single table lock to save memory. Concurrency collapses to one writer on that table — mass updates are done in batches to stay under the threshold."),
("Intermediate","An order-processing system hits nightly deadlocks. Walk through your approach.","Pull deadlock graphs from system_health to see the exact statements and resources in the cycle. Typical fixes: make all code paths touch tables in the same order, shorten transactions (writes last), add missing indexes so updates don't scan, consider RCSI to take readers out of the picture, and add 1205 retry logic as a safety net."),
("Intermediate","AFTER vs INSTEAD OF triggers?","AFTER runs post-statement (per statement, with constraints already checked) — right for auditing and bookkeeping. INSTEAD OF replaces the triggering action entirely — the base operation only happens if the trigger performs it; used for soft deletes and making multi-table views updatable. Only one INSTEAD OF trigger per action per table."),
("Intermediate","Why do most teams keep business logic out of triggers?","Triggers are invisible at the call site, hard to unit test, fire per statement (inviting multi-row bugs), add cost to every write, can cascade into other triggers, and their ordering is only partly controllable. Auditing and sync duties stay; decisions and workflows move to procedures or services where they're explicit.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Table-valued parameters, temp tables vs table variables, SELECT INTO",
"Pass whole tables into procedures with TVPs (from T-SQL and from C#), choose correctly between #temp tables and @table variables, and use SELECT INTO for quick materialisation.",
[("Table-valued parameter (TVP)","A procedure parameter whose type is a user-defined <i>table type</i> — the clean way to pass many rows in one call."),
("Table type","<code>CREATE TYPE x AS TABLE (…)</code>: a saved table definition (columns, PK, CHECK) that TVPs and variables can use."),
("READONLY","Mandatory keyword on TVP parameters: the proc may read and join the TVP but never modify it."),
("Temp table (#t)","A real table created in tempdb, visible to the creating session (and procs it calls), dropped when the session/scope ends."),
("Global temp table (##t)","Visible to <i>all</i> sessions; dropped when the creator disconnects and no one else is using it. Rare; mostly for debugging."),
("Table variable (@t)","A variable holding rows, also stored in tempdb, scoped to the batch/proc. Not affected by ROLLBACK."),
("tempdb","The shared scratch database where temp tables, table variables, version stores and spills live. One per instance — a common bottleneck."),
("Statistics","Histograms about column values the optimiser uses to estimate row counts. Temp tables have them; table variables don't."),
("Recompile","Re-optimisation of a statement. Temp-table changes can trigger recompiles (cost, but fresher plans); table variables avoid them (stale guesses instead)."),
("Deferred compilation","SQL Server 2019+: statements referencing table variables compile when first executed, using the variable's <i>actual</i> row count instead of a guess of 1."),
("SELECT INTO","Creates a brand-new table from a query's shape and rows in one statement: <code>SELECT … INTO #t FROM …</code>."),
("SqlDbType.Structured","The ADO.NET parameter type for TVPs — pass a DataTable (or DbDataReader / IEnumerable of SqlDataRecord) and name the server-side table type."),
("STRING_SPLIT","2016+ function turning 'a,b,c' into rows; 2022 adds an ordinal column. The budget alternative when a TVP is overkill.")],
["One proc call with a 500-row TVP beats 500 single-row calls — fewer round trips, one transaction, one plan.",
"A table type can't be ALTERed while anything references it: create <code>TypeName_v2</code>, migrate procs, drop the old one. Design types small and stable.",
"TVP parameters are READONLY — to modify the data, copy it into a temp table first.",
"#temp tables: statistics, indexes, parallel plans, rolled back with transactions. @table variables: no stats, survive ROLLBACK, fewer recompiles.",
"Default: temp table when rows are many or the query is complex; table variable for a handful of rows or when ROLLBACK-survival is the point (e.g. error logging).",
"SELECT INTO copies column names/types (and IDENTITY) but no constraints, defaults or indexes."],
f'''
<h3>1. The problem: passing a list to SQL</h3>
{C(r"""
-- The old hacks, before TVPs:
-- 1) CSV string + STRING_SPLIT (2016+). Works, but everything is a string:
DECLARE @csv NVARCHAR(100) = N'2,4,7';
SELECT e.EmployeeId, e.FirstName
FROM dbo.Employees e
JOIN STRING_SPLIT(@csv, ',') s ON s.value = e.EmployeeId;  -- implicit convert on every row

-- 2) One call per id from the app: N round trips, N plans, no shared transaction.
-- 3) Dynamic SQL: 'WHERE EmployeeId IN (' + @csv + ')' -- injection + plan-cache pollution.
""", "csv-hack.sql", lang="sql")}
<p>All three lose typing, performance or safety. A TVP keeps all three: the client sends <i>rows</i>, typed, in one go.</p>

<h3>2. Table types and TVPs in T-SQL</h3>
{C(r"""
CREATE TYPE dbo.IntList AS TABLE
(
    Id INT NOT NULL PRIMARY KEY     -- PK: free uniqueness + an index for the join
);
GO
CREATE OR ALTER PROCEDURE dbo.usp_GetEmployeesByIds
    @Ids dbo.IntList READONLY        -- READONLY is mandatory for TVPs
AS
BEGIN
    SET NOCOUNT ON;
    SELECT e.EmployeeId, e.FirstName, e.LastName, e.Salary
    FROM dbo.Employees e
    JOIN @Ids i ON i.Id = e.EmployeeId
    ORDER BY e.EmployeeId;
END
GO
-- Calling it from T-SQL:
DECLARE @wanted dbo.IntList;
INSERT @wanted (Id) VALUES (2), (4), (7);
EXEC dbo.usp_GetEmployeesByIds @Ids = @wanted;
""", "tvp.sql", lang="sql")}
{C(r"""
EmployeeId  FirstName   LastName    Salary
----------- ----------- ----------- -----------
2           Rahul       Mehta       72500.00
4           Divya       Kulkarni    58000.00
7           Sneha       Patil       61500.00
""", lang="text")}
{warn("You cannot <code>ALTER TYPE</code>. While any proc/function references dbo.IntList, you can't drop it either. Versioning strategy: create <code>dbo.IntList_v2</code>, repoint the procs, then drop the old type. Keep table types minimal so they rarely change.", "Note")}

<h3>3. Calling a TVP proc from C#</h3>
<p>The client-side half, with <code>Microsoft.Data.SqlClient</code> (NuGet). A <code>DataTable</code> whose columns match the table type is the simplest carrier:</p>
{C(r"""
using System.Data;
using Microsoft.Data.SqlClient;   // NuGet: Microsoft.Data.SqlClient

const string connectionString =
    "Server=localhost,1433;Database=HR;User Id=sa;Password=Your_Strong@Pass1;"
    + "TrustServerCertificate=True";

// 1. Build rows matching dbo.IntList (one INT column named Id)
var ids = new DataTable();
ids.Columns.Add("Id", typeof(int));
foreach (int id in (int[])[2, 4, 7])
    ids.Rows.Add(id);

// 2. Call the proc with a Structured parameter
await using var conn = new SqlConnection(connectionString);
await using var cmd = new SqlCommand("dbo.usp_GetEmployeesByIds", conn)
{
    CommandType = CommandType.StoredProcedure
};
var p = cmd.Parameters.Add("@Ids", SqlDbType.Structured);
p.TypeName = "dbo.IntList";       // the server-side table type
p.Value = ids;

await conn.OpenAsync();
await using var reader = await cmd.ExecuteReaderAsync();
while (await reader.ReadAsync())
    Console.WriteLine($"{reader.GetInt32(0),4}  {reader.GetString(1)} {reader.GetString(2)}");

//    2  Rahul Mehta
//    4  Divya Kulkarni
//    7  Sneha Patil
""", "TvpClient.cs")}
<p class="muted">The sandbox for this course has no SQL Server, so treat this as reviewed reference code: it targets .NET 8 with the <code>Microsoft.Data.SqlClient</code> package. For very large streams you can pass an <code>IEnumerable&lt;SqlDataRecord&gt;</code> instead of a DataTable and avoid materialising everything in memory.</p>

<h3>4. Temp tables (#t) vs table variables (@t)</h3>
{C(r"""
-- Both live in tempdb; behaviour differs where it matters:
CREATE TABLE #Big (Id INT PRIMARY KEY, Amount DECIMAL(10,2));
DECLARE @Small TABLE (Id INT PRIMARY KEY, Amount DECIMAL(10,2));

-- The ROLLBACK difference:
BEGIN TRANSACTION;
INSERT #Big   VALUES (1, 100);
INSERT @Small VALUES (1, 100);
ROLLBACK;

SELECT (SELECT COUNT(*) FROM #Big)   AS TempRows,    -- 0: rolled back
       (SELECT COUNT(*) FROM @Small) AS VarRows;     -- 1: table variables ignore ROLLBACK
""", "temp-vs-var.sql", lang="sql")}
{table(["","#Temp table","@Table variable"],[
["Statistics","Yes — optimiser estimates well","No — guessed 1 row (2019+: actual count at first compile, still no histograms)"],
["Indexes","Any, before or after filling","Only inline (PK/UNIQUE/INDEX at declaration)"],
["Transactions","Rolled back like a normal table","NOT affected by ROLLBACK"],
["Recompiles","Can trigger them (fresher plans, some cost)","Doesn't — one more reason plans can be stale"],
["Scope","Session + called procs; droppable","Current batch/proc only"],
["Parallel plans","Yes","Statements that modify a table variable run serially"],
["DDL after creation","ALTER TABLE works","None"],
["Good at","Big/filtered intermediate sets, complex joins","Few rows; surviving ROLLBACK (audit/logging); TVP cousins"]])}
{C(r"""
-- Why statistics matter: same 100k-row filter, different estimates
INSERT #Big   SELECT TOP (100000) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)), 1 FROM sys.all_columns a CROSS JOIN sys.all_columns b;
-- #Big: the optimiser KNOWS it's ~100k rows -> hash join, parallel plan
-- An equivalent @table variable: estimated 1 row (pre-2019) -> nested loops disaster
""", "stats-matter.sql", lang="sql")}
{tip("The ROLLBACK immunity is a feature: collect diagnostic rows into a table variable inside the transaction, ROLLBACK, and you still have the evidence to write into an error log.")}

<h3>5. SELECT INTO</h3>
{C(r"""
-- Create-and-fill in one statement: column names & types come from the SELECT
SELECT e.EmployeeId,
       e.FirstName + N' ' + e.LastName AS FullName,
       d.Name AS Department,
       e.Salary
INTO #HighEarners                      -- table must NOT already exist
FROM dbo.Employees e
JOIN dbo.Departments d ON d.DepartmentId = e.DepartmentId
WHERE e.Salary >= 70000;

SELECT * FROM #HighEarners;

-- vs INSERT INTO ... SELECT: the target must already exist (and keeps its constraints)
INSERT INTO dbo.EmployeeArchive (EmployeeId, FullName, Salary)
SELECT EmployeeId, FirstName + N' ' + LastName, Salary
FROM dbo.Employees WHERE IsActive = 0;
""", "select-into.sql", lang="sql")}
{ul(["SELECT INTO copies column names, types, NULLability and the IDENTITY property — but <b>no</b> constraints, defaults, indexes or triggers.",
"Great for ad-hoc snapshots and staging inside procs; add any needed indexes after the load.",
"To get just the shape without rows: <code>SELECT … INTO #t FROM src WHERE 1 = 0;</code>"])}

<h3>6. Choosing: TVP vs temp table vs table variable</h3>
{table(["Scenario","Reach for"],[
["App needs to send 200 order lines to one proc call","TVP"],
["Proc builds a 500k-row intermediate result, filters, joins back","#Temp table (stats + index)"],
["Loop bookkeeping of 20 rows inside a proc","@Table variable"],
["Keep diagnostics across a ROLLBACK","@Table variable"],
["Share working data with a proc you call","#Temp table (visible to callees — TVPs and variables aren't, unless passed)"],
["Quick copy of a query result to experiment on","SELECT INTO #t"],
["Comma-separated ids from a legacy caller","STRING_SPLIT, then join (validate numerics!)"]])}
''',
["Trying to UPDATE a TVP parameter inside the proc (it's READONLY — copy to a temp table if you must).",
"Using a table variable for 100k rows and getting a 1-row-estimate plan (pre-2019 especially).",
"Expecting @table variable contents to disappear on ROLLBACK (they survive).",
"ALTERing a table type — impossible; plan versioned types instead.",
"Rebuilding the same #temp table shape in ten procs instead of one shared definition (or a TVP type)."],
("40 min", ["Create <code>dbo.EmailList</code> table type (Email NVARCHAR(100) PK) and <code>usp_DeactivateByEmails</code> that flips IsActive = 0 for every matching employee and returns the affected rows. Call it from T-SQL with 3 emails, one of which doesn't exist.",
"Demonstrate the ROLLBACK difference yourself: fill #t and @t inside a transaction, roll back, count both. Then move the INSERTs before BEGIN TRAN and compare again.",
"Use SELECT INTO to snapshot all employees into <code>#Payroll</code>, add a computed 10% bonus column via ALTER TABLE + UPDATE, and join back to prove the base table never changed."]),
[("Why must a TVP parameter be READONLY?","SQL Server requires it: TVPs are passed by reference to row data the engine doesn't copy per call, so modification isn't supported. The proc can read and join the TVP; to change the data it must copy rows into a temp table or table variable."),
("Name three behavioural differences between #temp tables and @table variables.","Temp tables have statistics and support post-creation DDL/indexes; table variables don't (so estimates can be poor). Temp tables honour transaction ROLLBACK; table variables keep their rows. Temp tables are visible to procs you call; table variables are local to the batch/proc."),
("What does SELECT INTO copy and what does it not?","It creates the target with the SELECT's column names, types, NULLability and IDENTITY — but no PK/FK/CHECK constraints, defaults, indexes or triggers. Rows are inserted as part of the same statement.")],
[("Basic","What is a table-valued parameter and why use one?","A proc parameter typed by a user-defined table type, letting a caller send many typed rows in a single call — one round trip, one transaction, one plan — instead of CSV strings, XML or N separate calls. It must be declared READONLY."),
("Basic","How do you pass a TVP from .NET?","Create a parameter with SqlDbType.Structured, set TypeName to the server-side table type (e.g. dbo.IntList), and set Value to a DataTable, DbDataReader or IEnumerable&lt;SqlDataRecord&gt; whose columns match the type's definition, then execute the command as a stored procedure."),
("Basic","When would you pick a table variable over a temp table?","For small row counts where plan quality can't suffer much, inside functions (temp tables aren't allowed there), and when you need data to survive a ROLLBACK — e.g. capturing diagnostics before rolling back. Otherwise temp tables are the safer default for big or complex intermediates."),
("Intermediate","Why can table variables produce terrible query plans?","They have no statistics; before SQL Server 2019 the optimiser assumed 1 row regardless of contents, choosing nested-loop plans that explode on 100k rows. 2019's deferred compilation uses the actual row count at first execution, but there are still no histograms, so value-distribution estimates stay crude."),
("Intermediate","A proc builds a huge intermediate result used by three later queries. Temp table or CTE, and why?","A temp table: it materialises once, gets statistics (and optionally an index), and the three queries reuse it. A CTE is just inline query text — each reference re-expands and may re-execute the work. Materialise when reused or when stats will change join choices; stay inline for single-use."),
("Intermediate","How do TVPs interact with statistics and plans?","Like table variables, TVPs carry no statistics — the optimiser uses a fixed low estimate for them. For typical small TVPs that's fine; for large ones, copy the TVP into a #temp table inside the proc (gaining stats and indexes) before heavy joins, or accept OPTION (RECOMPILE) on the affected statement.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 2: sales schema + report procedures",
"Build the Sales schema (customers, products, orders, order lines) with seed data, then four production-style report procedures: OUTPUT totals, pagination, validated date ranges with THROW, and multiple result sets. Budget: about 4 hours.",
[("Schema (namespace)","A container inside a database: <code>Sales.Orders</code> vs <code>dbo.Employees</code>. Groups objects and simplifies permissions (GRANT on SCHEMA::Sales)."),
("Computed column","A column defined by an expression over other columns: <code>LineTotal AS (Qty * UnitPrice)</code>."),
("PERSISTED","Stores the computed value on disk (updated automatically) so it can be indexed and read cheaply."),
("OFFSET / FETCH","SQL paging: <code>ORDER BY … OFFSET n ROWS FETCH NEXT m ROWS ONLY</code> — ORDER BY is mandatory."),
("Multiple result sets","One proc, several SELECTs — the client reads them in order (NextResult in ADO.NET).")],
["Everything sales-related lives in a new <code>Sales</code> schema inside the same HR dev database.",
"<code>OrderLines.UnitPrice</code> copies the product's price at sale time — catalogue price changes must not rewrite history.",
"Every proc: <code>SET NOCOUNT ON;</code>, named <code>Sales.usp_…</code>, validates inputs with THROW before touching data.",
"Run the scripts in number order; each is re-runnable (CREATE OR ALTER / guarded inserts).",
"Tomorrow adds the transactional <code>usp_PlaceOrder</code> on top of this schema — keep it installed."],
f'''
<h3>Requirements</h3>
<ul>
<li>Schema <code>Sales</code> with <code>Customers</code>, <code>Products</code>, <code>Orders</code>, <code>OrderLines</code> — proper keys, FKs, CHECKs, and a persisted <code>LineTotal</code>.</li>
<li>Seed data: 6 customers, 8 products, 10 orders (Sep–Nov 2026) with 17 order lines.</li>
<li><code>usp_MonthlySalesSummary @Year, @Month</code> — OUTPUT order count + revenue, plus a per-customer result set.</li>
<li><code>usp_TopCustomers @PageNumber, @PageSize</code> — lifetime spend ranking with OFFSET/FETCH paging.</li>
<li><code>usp_ProductSales @FromDate, @ToDate</code> — THROW-validated date range, revenue per product.</li>
<li><code>usp_CustomerStatement @CustomerId</code> — three result sets: customer, orders, lifetime totals.</li>
</ul>

<h3>Layout and how to run</h3>
{C(r"""
sales-procs/
├─ 01_sales_schema.sql      -- schema + tables + indexes
├─ 02_sales_seed.sql        -- customers, products, orders, lines
├─ 03_report_procs.sql      -- the four procedures
├─ 04_run_reports.sql       -- calls with expected output
└─ README.md                -- tomorrow
""", lang="text")}
{C(r"""
# Run each file against the HR database, in order — VS Code MSSQL / SSMS, or sqlcmd:
docker cp sales-procs/. sql2022:/scripts/
docker exec -it sql2022 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa \
  -P 'Your_Strong@Pass1' -C -d HR -i /scripts/01_sales_schema.sql
# ...repeat for 02, 03, 04
""", lang="bash")}

<h3>Step 1 — Schema and tables</h3>
{C(r"""
USE HR;   -- dev convenience: same database, separate schema
GO
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'Sales')
    EXEC(N'CREATE SCHEMA Sales AUTHORIZATION dbo');
GO
CREATE TABLE Sales.Customers (
    CustomerId INT IDENTITY(1,1) CONSTRAINT PK_Customers PRIMARY KEY,
    Name       NVARCHAR(100) NOT NULL,
    City       NVARCHAR(50)  NOT NULL,
    Email      NVARCHAR(100) NOT NULL CONSTRAINT UQ_Customers_Email UNIQUE
);

CREATE TABLE Sales.Products (
    ProductId  INT IDENTITY(1,1) CONSTRAINT PK_Products PRIMARY KEY,
    Name       NVARCHAR(100) NOT NULL,
    Category   NVARCHAR(50)  NOT NULL,
    UnitPrice  DECIMAL(10,2) NOT NULL CONSTRAINT CK_Products_Price CHECK (UnitPrice > 0),
    StockQty   INT           NOT NULL CONSTRAINT CK_Products_Stock CHECK (StockQty >= 0)
);

CREATE TABLE Sales.Orders (
    OrderId    INT IDENTITY(1,1) CONSTRAINT PK_Orders PRIMARY KEY,
    CustomerId INT NOT NULL CONSTRAINT FK_Orders_Customers
               REFERENCES Sales.Customers (CustomerId),
    OrderDate  DATETIME2(0) NOT NULL CONSTRAINT DF_Orders_Date DEFAULT SYSDATETIME(),
    Status     NVARCHAR(20) NOT NULL CONSTRAINT DF_Orders_Status DEFAULT N'Placed'
               CONSTRAINT CK_Orders_Status CHECK (Status IN (N'Placed', N'Shipped', N'Cancelled'))
);

CREATE TABLE Sales.OrderLines (
    OrderLineId INT IDENTITY(1,1) CONSTRAINT PK_OrderLines PRIMARY KEY,
    OrderId     INT NOT NULL CONSTRAINT FK_OrderLines_Orders
                REFERENCES Sales.Orders (OrderId),
    ProductId   INT NOT NULL CONSTRAINT FK_OrderLines_Products
                REFERENCES Sales.Products (ProductId),
    Qty         INT NOT NULL CONSTRAINT CK_OrderLines_Qty CHECK (Qty > 0),
    UnitPrice   DECIMAL(10,2) NOT NULL,          -- price AT SALE TIME, copied from Products
    LineTotal   AS (Qty * UnitPrice) PERSISTED   -- computed once, stored, indexable
);

CREATE INDEX IX_Orders_CustomerId     ON Sales.Orders (CustomerId);
CREATE INDEX IX_Orders_OrderDate      ON Sales.Orders (OrderDate);
CREATE INDEX IX_OrderLines_OrderId    ON Sales.OrderLines (OrderId);
CREATE INDEX IX_OrderLines_ProductId  ON Sales.OrderLines (ProductId);
""", "01_sales_schema.sql", lang="sql")}

<h3>Step 2 — Seed data</h3>
{C(r"""
USE HR;
GO
-- Re-runnable: wipe children first (dev only!)
DELETE Sales.OrderLines; DELETE Sales.Orders;
DELETE Sales.Products;   DELETE Sales.Customers;
DBCC CHECKIDENT ('Sales.Orders', RESEED, 0);
DBCC CHECKIDENT ('Sales.OrderLines', RESEED, 0);
DBCC CHECKIDENT ('Sales.Products', RESEED, 0);
DBCC CHECKIDENT ('Sales.Customers', RESEED, 0);

SET IDENTITY_INSERT Sales.Customers ON;
INSERT Sales.Customers (CustomerId, Name, City, Email) VALUES
 (1, N'Asha Verma',   N'Pune',    N'asha.verma@example.in'),
 (2, N'Ravi Iyer',    N'Chennai', N'ravi.iyer@example.in'),
 (3, N'Meena Joshi',  N'Indore',  N'meena.joshi@example.in'),
 (4, N'Imran Shaikh', N'Mumbai',  N'imran.shaikh@example.in'),
 (5, N'Neha Agarwal', N'Jaipur',  N'neha.agarwal@example.in'),
 (6, N'Rohit Bansal', N'Delhi',   N'rohit.bansal@example.in');
SET IDENTITY_INSERT Sales.Customers OFF;

SET IDENTITY_INSERT Sales.Products ON;
INSERT Sales.Products (ProductId, Name, Category, UnitPrice, StockQty) VALUES
 (1, N'Basmati Rice 5kg',    N'Grocery',     650.00, 100),
 (2, N'Masala Chai 250g',    N'Grocery',     180.00, 200),
 (3, N'A4 Paper Ream',       N'Stationery',  320.00, 150),
 (4, N'Gel Pen Pack (10)',   N'Stationery',  120.00, 300),
 (5, N'USB-C Cable 1m',      N'Electronics', 499.00,  80),
 (6, N'Wireless Mouse',      N'Electronics', 899.00,  60),
 (7, N'Steel Water Bottle',  N'Home',        550.00, 120),
 (8, N'LED Desk Lamp',       N'Home',       1250.00,  40);
SET IDENTITY_INSERT Sales.Products OFF;

SET IDENTITY_INSERT Sales.Orders ON;
INSERT Sales.Orders (OrderId, CustomerId, OrderDate, Status) VALUES
 ( 1, 2, '2026-09-10T11:05:00', N'Shipped'),
 ( 2, 5, '2026-09-21T15:40:00', N'Shipped'),
 ( 3, 1, '2026-10-03T09:12:00', N'Shipped'),
 ( 4, 2, '2026-10-07T18:25:00', N'Shipped'),
 ( 5, 3, '2026-10-12T10:00:00', N'Shipped'),
 ( 6, 1, '2026-10-18T20:31:00', N'Shipped'),
 ( 7, 4, '2026-10-25T13:44:00', N'Shipped'),
 ( 8, 6, '2026-11-02T12:02:00', N'Placed'),
 ( 9, 2, '2026-11-05T16:17:00', N'Placed'),
 (10, 5, '2026-11-09T09:55:00', N'Placed');
SET IDENTITY_INSERT Sales.Orders OFF;

-- UnitPrice copied from the catalogue at "sale time"
INSERT Sales.OrderLines (OrderId, ProductId, Qty, UnitPrice) VALUES
 ( 1, 1, 1,  650.00), ( 1, 2, 2, 180.00),
 ( 2, 4, 4,  120.00), ( 2, 8, 1, 1250.00),
 ( 3, 1, 2,  650.00), ( 3, 6, 1,  899.00),
 ( 4, 4, 5,  120.00), ( 4, 3, 2,  320.00),
 ( 5, 8, 1, 1250.00),
 ( 6, 2, 3,  180.00), ( 6, 7, 1,  550.00),
 ( 7, 5, 2,  499.00), ( 7, 6, 1,  899.00),
 ( 8, 6, 1,  899.00), ( 8, 5, 1,  499.00),
 ( 9, 7, 2,  550.00),
 (10, 1, 1,  650.00), (10, 3, 1,  320.00), (10, 4, 2, 120.00);

SELECT (SELECT COUNT(*) FROM Sales.Orders)     AS Orders,       -- 10
       (SELECT COUNT(*) FROM Sales.OrderLines) AS Lines,        -- 19
       (SELECT SUM(LineTotal) FROM Sales.OrderLines) AS Revenue; -- 16424.00
""", "02_sales_seed.sql", lang="sql")}

<h3>Step 3 — usp_MonthlySalesSummary (OUTPUT totals)</h3>
{C(r"""
CREATE OR ALTER PROCEDURE Sales.usp_MonthlySalesSummary
    @Year         INT,
    @Month        INT,
    @OrderCount   INT           OUTPUT,
    @TotalRevenue DECIMAL(12,2) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    IF @Month NOT BETWEEN 1 AND 12
        THROW 50001, N'@Month must be between 1 and 12.', 1;
    IF @Year NOT BETWEEN 2000 AND 2100
        THROW 50002, N'@Year must be between 2000 and 2100.', 1;

    DECLARE @From DATE = DATEFROMPARTS(@Year, @Month, 1);
    DECLARE @To   DATE = DATEADD(MONTH, 1, @From);    -- half-open range [From, To)

    SELECT @OrderCount   = COUNT(DISTINCT o.OrderId),
           @TotalRevenue = COALESCE(SUM(ol.LineTotal), 0)
    FROM Sales.Orders o
    JOIN Sales.OrderLines ol ON ol.OrderId = o.OrderId
    WHERE o.OrderDate >= @From AND o.OrderDate < @To
      AND o.Status <> N'Cancelled';

    -- Breakdown result set: who bought how much this month
    SELECT c.Name AS Customer,
           COUNT(DISTINCT o.OrderId) AS Orders,
           SUM(ol.LineTotal)         AS Revenue
    FROM Sales.Orders o
    JOIN Sales.Customers  c  ON c.CustomerId = o.CustomerId
    JOIN Sales.OrderLines ol ON ol.OrderId   = o.OrderId
    WHERE o.OrderDate >= @From AND o.OrderDate < @To
      AND o.Status <> N'Cancelled'
    GROUP BY c.Name
    ORDER BY Revenue DESC;
END
""", "03_report_procs.sql — part 1", lang="sql")}
{tip("The half-open range <code>&gt;= first-of-month AND &lt; first-of-next-month</code> works for DATE, DATETIME2 and any precision — no BETWEEN edge cases at 23:59:59.997.")}

<h3>Step 4 — usp_TopCustomers (pagination)</h3>
{C(r"""
CREATE OR ALTER PROCEDURE Sales.usp_TopCustomers
    @PageNumber INT = 1,
    @PageSize   INT = 3
AS
BEGIN
    SET NOCOUNT ON;

    IF @PageNumber < 1               THROW 50003, N'@PageNumber must be >= 1.', 1;
    IF @PageSize NOT BETWEEN 1 AND 100 THROW 50004, N'@PageSize must be 1-100.', 1;

    SELECT c.CustomerId, c.Name, c.City,
           COUNT(DISTINCT o.OrderId) AS Orders,
           SUM(ol.LineTotal)         AS TotalSpend,
           COUNT(*) OVER ()          AS TotalCustomers   -- same on every row: rank size
    FROM Sales.Customers c
    JOIN Sales.Orders o      ON o.CustomerId = c.CustomerId AND o.Status <> N'Cancelled'
    JOIN Sales.OrderLines ol ON ol.OrderId   = o.OrderId
    GROUP BY c.CustomerId, c.Name, c.City
    ORDER BY TotalSpend DESC, c.CustomerId          -- deterministic tiebreak!
    OFFSET (@PageNumber - 1) * @PageSize ROWS
    FETCH NEXT @PageSize ROWS ONLY;
END
""", "03_report_procs.sql — part 2", lang="sql")}
{warn("Pagination without a deterministic ORDER BY (unique tiebreak column) can show the same customer on two pages or skip one. And OFFSET still <i>reads</i> all skipped rows — fine here, a real cost at page 10,000 (keyset paging fixes that; Week 14).", "Note")}

<h3>Step 5 — usp_ProductSales (validated range) and usp_CustomerStatement (multiple result sets)</h3>
{C(r"""
CREATE OR ALTER PROCEDURE Sales.usp_ProductSales
    @FromDate DATE,
    @ToDate   DATE
AS
BEGIN
    SET NOCOUNT ON;

    IF @FromDate IS NULL OR @ToDate IS NULL
        THROW 50005, N'@FromDate and @ToDate are both required.', 1;
    IF @FromDate > @ToDate
        THROW 50006, N'@FromDate must be on or before @ToDate.', 1;

    SELECT p.ProductId, p.Name, p.Category,
           SUM(ol.Qty)       AS UnitsSold,
           SUM(ol.LineTotal) AS Revenue
    FROM Sales.OrderLines ol
    JOIN Sales.Orders   o ON o.OrderId   = ol.OrderId
    JOIN Sales.Products p ON p.ProductId = ol.ProductId
    WHERE o.OrderDate >= @FromDate
      AND o.OrderDate <  DATEADD(DAY, 1, @ToDate)   -- include the whole @ToDate day
      AND o.Status <> N'Cancelled'
    GROUP BY p.ProductId, p.Name, p.Category
    ORDER BY Revenue DESC;
END
GO
CREATE OR ALTER PROCEDURE Sales.usp_CustomerStatement
    @CustomerId INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Sales.Customers WHERE CustomerId = @CustomerId)
        THROW 50007, N'Customer not found.', 1;

    -- Result set 1: the customer
    SELECT CustomerId, Name, City, Email
    FROM Sales.Customers WHERE CustomerId = @CustomerId;

    -- Result set 2: their orders with totals
    SELECT o.OrderId, o.OrderDate, o.Status, SUM(ol.LineTotal) AS OrderTotal
    FROM Sales.Orders o
    JOIN Sales.OrderLines ol ON ol.OrderId = o.OrderId
    WHERE o.CustomerId = @CustomerId
    GROUP BY o.OrderId, o.OrderDate, o.Status
    ORDER BY o.OrderDate;

    -- Result set 3: lifetime totals
    SELECT COUNT(DISTINCT o.OrderId)      AS Orders,
           COALESCE(SUM(ol.LineTotal), 0) AS LifetimeSpend
    FROM Sales.Orders o
    JOIN Sales.OrderLines ol ON ol.OrderId = o.OrderId
    WHERE o.CustomerId = @CustomerId;
END
""", "03_report_procs.sql — part 3", lang="sql")}

<h3>Step 6 — Run it</h3>
{C(r"""
DECLARE @orders INT, @revenue DECIMAL(12,2);
EXEC Sales.usp_MonthlySalesSummary @Year = 2026, @Month = 10,
     @OrderCount = @orders OUTPUT, @TotalRevenue = @revenue OUTPUT;
SELECT @orders AS Orders, @revenue AS Revenue;

EXEC Sales.usp_TopCustomers @PageNumber = 1, @PageSize = 3;
EXEC Sales.usp_ProductSales @FromDate = '2026-10-01', @ToDate = '2026-10-31';
EXEC Sales.usp_CustomerStatement @CustomerId = 2;
EXEC Sales.usp_ProductSales @FromDate = '2026-11-01', @ToDate = '2026-10-01';  -- must fail
""", "04_run_reports.sql", lang="sql")}
{C(r"""
-- Example output (matches the seed data exactly)

-- Monthly summary, October 2026 — breakdown result set, then the OUTPUTs:
Customer       Orders  Revenue
-------------- ------- ---------
Asha Verma     2       3289.00
Imran Shaikh   1       1897.00
Meena Joshi    1       1250.00
Ravi Iyer      1       1240.00

Orders  Revenue
------- ---------
5       7676.00

-- Top customers, page 1 of 2 (TotalCustomers = 6):
CustomerId  Name          City     Orders  TotalSpend  TotalCustomers
----------- ------------- -------- ------- ----------- --------------
2           Ravi Iyer     Chennai  3       3350.00     6
1           Asha Verma    Pune     2       3289.00     6
5           Neha Agarwal  Jaipur   2       2940.00     6

-- Product sales for October 2026 (top rows):
ProductId  Name              Category     UnitsSold  Revenue
---------- ----------------- ------------ ---------- ---------
6          Wireless Mouse    Electronics  2          1798.00
1          Basmati Rice 5kg  Grocery      2          1300.00
8          LED Desk Lamp     Home         1          1250.00
5          USB-C Cable 1m    Electronics  2           998.00

-- Customer statement for Ravi Iyer: 3 result sets
CustomerId  Name       City     Email
----------- ---------- -------- --------------------
2           Ravi Iyer  Chennai  ravi.iyer@example.in

OrderId  OrderDate            Status   OrderTotal
-------- -------------------- -------- -----------
1        2026-09-10 11:05:00  Shipped  1010.00
4        2026-10-07 18:25:00  Shipped  1240.00
9        2026-11-05 16:17:00  Placed   1100.00

Orders  LifetimeSpend
------- --------------
3       3350.00

-- The bad date range:
Msg 50006, Level 16, State 1, Procedure Sales.usp_ProductSales, Line 10
@FromDate must be on or before @ToDate.
""", lang="text")}

<h3>Stretch goals</h3>
<ul>
<li>Add <code>@Category NVARCHAR(50) = NULL</code> to <code>usp_ProductSales</code> as an optional filter (Monday's catch-all pattern).</li>
<li>Create a <code>SalesReader</code> database role, <code>GRANT EXECUTE ON SCHEMA::Sales</code> to it, and verify a test user can run reports but not SELECT from the tables.</li>
<li>Add a per-day result set to the monthly summary (GROUP BY CAST(OrderDate AS DATE)).</li>
<li>Export October's product sales to CSV with <code>sqlcmd -s"," -W -Q "EXEC Sales.usp_ProductSales ..."</code>.</li>
</ul>
''',
iqs=[("Basic","Why copy UnitPrice into OrderLines instead of joining to Products for totals?","Catalogue prices change; invoices must not. Copying the price at sale time makes each order line a historical fact — reports and totals stay stable, and the CHECK/computed LineTotal is self-contained. Joining to Products would silently rewrite old revenue whenever a price is updated."),
("Basic","How does a .NET caller read usp_CustomerStatement's three result sets?","ExecuteReader returns the first set; reader.NextResult() advances to the next, in the exact order the proc SELECTed them. Dapper's QueryMultiple wraps the same mechanism. Result-set order and shape are part of the proc's contract — changing them breaks callers."),
("Intermediate","When totals are needed by the app, OUTPUT parameters or another result set?","OUTPUT parameters are cheapest for a few scalars and read naturally in ADO.NET after the reader closes. A result set is better when the \"totals\" are really rows (per-group totals) or when the client API makes extra result sets easier than parameter plumbing. Avoid returning the same numbers both ways — one source of truth."),
("Intermediate","What are the pitfalls of OFFSET/FETCH pagination?","It requires a deterministic ORDER BY (add a unique tiebreak) or pages can overlap/skip; the engine still reads and discards all skipped rows, so deep pages get slower linearly; and concurrent inserts shift rows between pages. Keyset (seek-based) pagination — WHERE (SpendRank, Id) &gt; last-seen — fixes the depth cost for infinite-scroll patterns.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "usp_PlaceOrder: an all-or-nothing order pipeline",
"Finish the project: a transactional order-placing procedure fed by a TVP — stock validation, atomic insert + decrement, XACT_ABORT + TRY/CATCH, a deadlock-retry wrapper, and tests that prove failures change nothing. Budget: about 4 hours.",
[("All-or-nothing","The order header, its lines and the stock decrements commit together or not at all — the week's transaction skills, applied."),
("UPDLOCK hint","Read rows taking update locks instead of shared ones: \"I will write these rows\" — two sessions can't both pass the stock check."),
("HOLDLOCK hint","Hold the locks to end of transaction (serializable semantics for those rows) — the gap between check and update stays protected."),
("Oversell","Selling more stock than exists — exactly what the check-then-act race produces without proper locking."),
("Retry policy","Re-running a transaction that failed transiently (deadlock 1205, snapshot conflict 3960) a bounded number of times with a delay.")],
["<code>SET XACT_ABORT ON</code> + TRY/CATCH + bare <code>THROW;</code> — Tuesday's template, now in production shape.",
"The TVP's PRIMARY KEY on ProductId means duplicate lines are rejected before the proc even runs.",
"Stock is checked <i>with UPDLOCK</i> inside the transaction — checking before the transaction would be a race.",
"Every failure path must leave zero traces: no order row, no lines, unchanged stock. The tests prove it.",
"Deadlock retries wrap the <b>whole transaction</b>, never a statement inside it."],
f'''
<h3>Step 1 — Table type and the procedure</h3>
{C(r"""
USE HR;
GO
CREATE TYPE Sales.OrderLineInput AS TABLE
(
    ProductId INT NOT NULL PRIMARY KEY,    -- PK: no duplicate products per order
    Qty       INT NOT NULL CHECK (Qty > 0)
);
GO
CREATE OR ALTER PROCEDURE Sales.usp_PlaceOrder
    @CustomerId INT,
    @Lines      Sales.OrderLineInput READONLY,
    @OrderId    INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;      -- timeouts/severe errors roll back instead of leaking locks

    -- Cheap validations first, outside the transaction
    IF NOT EXISTS (SELECT 1 FROM Sales.Customers WHERE CustomerId = @CustomerId)
        THROW 50020, N'Customer does not exist.', 1;

    IF NOT EXISTS (SELECT 1 FROM @Lines)
        THROW 50021, N'An order needs at least one line.', 1;

    IF EXISTS (SELECT 1 FROM @Lines l
               WHERE NOT EXISTS (SELECT 1 FROM Sales.Products p
                                 WHERE p.ProductId = l.ProductId))
        THROW 50022, N'One or more product ids do not exist.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Stock check WITH LOCKS: UPDLOCK reserves the rows we'll update,
        -- HOLDLOCK keeps that reservation until COMMIT. Without these, two
        -- concurrent orders could both pass the check and oversell.
        IF EXISTS (SELECT 1
                   FROM Sales.Products p WITH (UPDLOCK, HOLDLOCK)
                   JOIN @Lines l ON l.ProductId = p.ProductId
                   WHERE p.StockQty < l.Qty)
            THROW 50023, N'Insufficient stock for one or more products.', 1;

        INSERT Sales.Orders (CustomerId) VALUES (@CustomerId);
        SET @OrderId = SCOPE_IDENTITY();

        INSERT Sales.OrderLines (OrderId, ProductId, Qty, UnitPrice)
        SELECT @OrderId, l.ProductId, l.Qty, p.UnitPrice     -- price at sale time
        FROM @Lines l
        JOIN Sales.Products p ON p.ProductId = l.ProductId;

        UPDATE p
        SET p.StockQty = p.StockQty - l.Qty
        FROM Sales.Products p
        JOIN @Lines l ON l.ProductId = p.ProductId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @OrderId = NULL;     -- never hand back an id that was rolled back
        THROW;
    END CATCH;
END
""", "05_place_order.sql", lang="sql")}
<p>Note the order inside the transaction: lock + check, then header, then lines, then stock. Every caller that touches Products and Orders in this same sequence can block briefly but never deadlock with a twin of itself — Thursday's resource-ordering rule.</p>

<h3>Step 2 — Happy path</h3>
{C(r"""
DECLARE @lines Sales.OrderLineInput;
INSERT @lines (ProductId, Qty) VALUES (5, 2), (7, 1);   -- 2 cables, 1 bottle

DECLARE @orderId INT;
EXEC Sales.usp_PlaceOrder @CustomerId = 3, @Lines = @lines, @OrderId = @orderId OUTPUT;

SELECT @orderId AS NewOrderId;
SELECT ol.ProductId, ol.Qty, ol.UnitPrice, ol.LineTotal
FROM Sales.OrderLines ol WHERE ol.OrderId = @orderId;
SELECT ProductId, StockQty FROM Sales.Products WHERE ProductId IN (5, 7);
""", "06_place_order_tests.sql — test 1", lang="sql")}
{C(r"""
NewOrderId
-----------
11

ProductId  Qty  UnitPrice  LineTotal
---------- ---- ---------- ----------
5          2    499.00     998.00
7          1    550.00     550.00

ProductId  StockQty
---------- ---------
5          78        -- was 80
7          119       -- was 120
""", lang="text")}

<h3>Step 3 — Forcing failures (and proving nothing changed)</h3>
{C(r"""
-- Test 2: insufficient stock (only 40 lamps exist)
DECLARE @greedy Sales.OrderLineInput;
INSERT @greedy (ProductId, Qty) VALUES (8, 999);
DECLARE @orderId INT;
EXEC Sales.usp_PlaceOrder @CustomerId = 1, @Lines = @greedy, @OrderId = @orderId OUTPUT;
""", "06_place_order_tests.sql — test 2", lang="sql")}
{C(r"""
Msg 50023, Level 16, State 1, Procedure Sales.usp_PlaceOrder, Line 27
Insufficient stock for one or more products.
""", lang="text")}
{C(r"""
-- Test 3: one good line + one bad line => the WHOLE order must vanish
DECLARE @mixed Sales.OrderLineInput;
INSERT @mixed (ProductId, Qty) VALUES (1, 1),      -- fine: 97 in stock
                                     (8, 999);     -- impossible
DECLARE @orderId INT;
EXEC Sales.usp_PlaceOrder @CustomerId = 1, @Lines = @mixed, @OrderId = @orderId OUTPUT;
-- Msg 50023 again. Now PROVE atomicity:
SELECT MAX(OrderId) AS LastOrder FROM Sales.Orders;          -- still 11
SELECT StockQty FROM Sales.Products WHERE ProductId IN (1, 8); -- 97 and 40: untouched

-- Test 4: unknown product id
DECLARE @ghost Sales.OrderLineInput;
INSERT @ghost (ProductId, Qty) VALUES (42, 1);
EXEC Sales.usp_PlaceOrder @CustomerId = 1, @Lines = @ghost, @OrderId = @orderId OUTPUT;
-- Msg 50022: One or more product ids do not exist.

-- Test 5: unknown customer
DECLARE @ok Sales.OrderLineInput;
INSERT @ok (ProductId, Qty) VALUES (1, 1);
EXEC Sales.usp_PlaceOrder @CustomerId = 99, @Lines = @ok, @OrderId = @orderId OUTPUT;
-- Msg 50020: Customer does not exist.

-- Test 6: empty basket
DECLARE @empty Sales.OrderLineInput;
EXEC Sales.usp_PlaceOrder @CustomerId = 1, @Lines = @empty, @OrderId = @orderId OUTPUT;
-- Msg 50021: An order needs at least one line.
""", "06_place_order_tests.sql — tests 3-6", lang="sql")}

<h3>Step 4 — Deadlock-retry wrapper</h3>
{C(r"""
-- How the application (or a job) should call usp_PlaceOrder:
DECLARE @lines Sales.OrderLineInput;
INSERT @lines (ProductId, Qty) VALUES (6, 1);

DECLARE @orderId  INT,
        @attempt  INT = 1,
        @maxTries INT = 3;

WHILE @attempt <= @maxTries
BEGIN
    BEGIN TRY
        EXEC Sales.usp_PlaceOrder @CustomerId = 6, @Lines = @lines, @OrderId = @orderId OUTPUT;
        PRINT CONCAT('Order ', @orderId, ' placed on attempt ', @attempt);
        BREAK;                                   -- success: leave the loop
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (1205, 3960)        -- deadlock victim / snapshot conflict
           AND @attempt < @maxTries
        BEGIN
            PRINT CONCAT('Transient error ', ERROR_NUMBER(), ' — retrying...');
            WAITFOR DELAY '00:00:00.200';        -- small backoff before retry
            SET @attempt += 1;
        END
        ELSE
            THROW;    -- business errors (50020-50023) or retries exhausted: fail loudly
    END CATCH;
END
""", "07_place_order_retry.sql", lang="sql")}
<p>Only <b>transient</b> errors are retried; business errors like insufficient stock would fail identically every time. In the .NET weeks this same policy moves into C# (Polly) — the shape stays: bounded attempts, backoff, retry the whole unit of work.</p>

<h3>Step 5 — Try to break it</h3>
{table(["Attack","Expected result"],[
["Qty = 0 in the TVP","Rejected at <code>INSERT @lines</code> by the type's CHECK — the proc never runs"],
["Same ProductId twice in the TVP","PK violation on the table type at INSERT — duplicates impossible"],
["Customer 99","Error 50020, nothing written"],
["Product 42","Error 50022, nothing written"],
["Qty 999 of product 8","Error 50023; order count and stock provably unchanged"],
["One good + one impossible line","Whole order rejected — atomicity, not partial fulfilment"],
["Call without OUTPUT on @OrderId","Proc succeeds but caller's variable stays NULL — Monday's silent gotcha"],
["Two sessions buy the last unit simultaneously","UPDLOCK serialises them: first wins, second gets 50023 — no oversell"],
["KILL the session mid-proc","XACT_ABORT rolls everything back; no orphan order, no locks left behind"],
["Deadlock engineered with another proc","Victim gets 1205; the retry wrapper replays it successfully"]])}

<h3>Step 6 — README and git</h3>
{C(r"""
# Sales Procs (Week 13)

Stored-procedure layer over a small sales schema: reporting procs
(OUTPUT totals, pagination, validated ranges, multi-result statements)
and a transactional, TVP-fed order-placing pipeline.

## Objects
| Script | Contents |
|---|---|
| 01_sales_schema.sql | Sales schema: Customers, Products, Orders, OrderLines |
| 02_sales_seed.sql | Seed data (6 customers, 8 products, 10 orders) |
| 03_report_procs.sql | usp_MonthlySalesSummary, usp_TopCustomers, usp_ProductSales, usp_CustomerStatement |
| 05_place_order.sql | Sales.OrderLineInput TVP type + usp_PlaceOrder |
| 06_place_order_tests.sql | Happy path + 5 failure tests (all leave zero traces) |
| 07_place_order_retry.sql | Deadlock/transient retry wrapper |

## Run
SQL Server 2022 (Docker), database HR. Execute scripts in number order
(sqlcmd -i or SSMS). 04_run_reports.sql prints the expected outputs.

## Design notes
- OrderLines.UnitPrice freezes the sale-time price; LineTotal is persisted computed.
- usp_PlaceOrder: XACT_ABORT + TRY/CATCH/THROW; stock checked under UPDLOCK, HOLDLOCK.
- Errors 50020-50023 are business errors; only 1205/3960 are retried.
""", "README.md", lang="text")}
{C(r"""
cd sales-procs
git init
git add .
git commit -m "Week 13: sales schema, report procs, transactional usp_PlaceOrder"
git remote add origin https://github.com/nayak22/sales-procs.git
git push -u origin main
""", lang="bash")}

<h3>Week 13 revision checklist</h3>
<ul>
<li>Proc anatomy: CREATE OR ALTER, defaults, OUTPUT (both ends!), RETURN codes, INSERT…EXEC, SET NOCOUNT ON, why not sp_</li>
<li>TRY/CATCH limits; ERROR_* functions; THROW vs RAISERROR; bare THROW rethrow; XACT_ABORT; XACT_STATE −1/0/1</li>
<li>ACID; @@TRANCOUNT mechanics; why nested transactions are a myth; error 266; savepoints</li>
<li>Isolation ladder vs the three anomalies; two-session demos; SNAPSHOT vs RCSI and the version store</li>
<li>Lock modes S/U/X/intent; escalation; finding blockers; deadlock cycle, graph, 1205, ordering + retry</li>
<li>Triggers: per-statement, inserted/deleted, audit pattern, INSTEAD OF, why business logic stays out</li>
<li>TVPs (type + READONLY + Structured from C#); #temp vs @table differences; SELECT INTO</li>
</ul>

<h3>Quiz — predict the output / does it run?</h3>
<details><summary>Q1. What does the last SELECT print?</summary>
{C(r"""
BEGIN TRANSACTION;
BEGIN TRANSACTION;
COMMIT;
SELECT @@TRANCOUNT;
""", lang="sql")}<b>1.</b> The inner COMMIT only decremented the counter from 2 to 1 — nothing committed, one real transaction is still open (and still needs a COMMIT or ROLLBACK).</details>
<details><summary>Q2. What are tv and tt?</summary>
{C(r"""
DECLARE @t TABLE (n INT);
CREATE TABLE #t (n INT);
BEGIN TRANSACTION;
INSERT @t VALUES (1);
INSERT #t VALUES (1);
ROLLBACK;
SELECT (SELECT COUNT(*) FROM @t) AS tv,
       (SELECT COUNT(*) FROM #t) AS tt;
""", lang="sql")}<b>tv = 1, tt = 0.</b> Table variables are not affected by ROLLBACK; temp tables are real tables and roll back normally.</details>
<details><summary>Q3. What prints?</summary>
{C(r"""
BEGIN TRY
    RAISERROR (N'heads up', 10, 1);
    PRINT 'A';
END TRY
BEGIN CATCH
    PRINT 'B';
END CATCH;
""", lang="sql")}<b>heads up, then A.</b> Severity 10 is informational — it never transfers control to CATCH, so execution continues in the TRY block. At severity 16 the output would be just B.</details>
<details><summary>Q4. Does this run?</summary>
{C(r"""
SELECT ProductId, Name
FROM Sales.Products
OFFSET 3 ROWS FETCH NEXT 3 ROWS ONLY;
""", lang="sql")}<b>No.</b> OFFSET/FETCH is a clause of ORDER BY — without an ORDER BY it's a syntax error (\"Invalid usage of the option NEXT…\"). Add <code>ORDER BY ProductId</code> and it returns products 4–6.</details>
<details><summary>Q5. The CATCH block intends to roll back and rethrow. What actually happens?</summary>
{C(r"""
BEGIN CATCH
    ROLLBACK TRANSACTION
    THROW
END CATCH;
""", lang="sql")}<b>No rethrow — it parses as <code>ROLLBACK TRANSACTION THROW</code>.</b> THROW isn't a reserved keyword, so it's taken as a transaction/savepoint name; you get \"Cannot roll back THROW…\" (and the original error is masked). Terminate the statement: <code>ROLLBACK TRANSACTION; THROW;</code></details>

<div class="note tip"><b>Next week:</b> Week 14 — Indexing and performance: clustered vs nonclustered indexes, included columns and covering queries, reading execution plans, SARGability, statistics, and hunting slow queries — including why Monday's catch-all search pattern and parameter sniffing behave the way they do.</div>
''',
iqs=[("Basic","Walk through how usp_PlaceOrder guarantees all-or-nothing.","Validations THROW before any write. The writes run inside one explicit transaction under SET XACT_ABORT ON; any error enters CATCH, which rolls back and rethrows — so header, lines and stock decrements exist together or not at all. XACT_ABORT also covers client timeouts that TRY/CATCH never sees."),
("Intermediate","Why does the stock check read with UPDLOCK and HOLDLOCK?","Plain shared locks would let two sessions both pass the check for the last unit, then both decrement — overselling. UPDLOCK makes the check take update locks (mutually exclusive between checkers), and HOLDLOCK keeps them until COMMIT, closing the gap between check and update. The second session waits, re-reads the decremented stock, and correctly fails."),
("Intermediate","Where should deadlock retry logic live, and what must it never do?","Around the whole transaction — in the calling layer (T-SQL wrapper or application code), because error 1205 rolls back the entire transaction, so retrying a single statement is meaningless. It must never retry non-transient business errors, never retry unboundedly, and should back off briefly between attempts."),
("Intermediate","Why a TVP for the order lines rather than JSON or repeated calls?","A TVP arrives typed and set-oriented: the proc joins it like a table, the type's PK/CHECK reject bad shapes before execution, and the whole basket travels in one call inside one transaction. JSON needs parsing and validation in the proc; N calls per line lose atomicity unless the app manages the transaction, plus N round trips.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Stored procedures","Stored procedures","CREATE OR ALTER, defaults, OUTPUT, RETURN codes, EXEC, NOCOUNT, sp_ anti-pattern.","2 hrs"),
 (2,"TUE","Error handling: TRY/CATCH and THROW","TRY · CATCH · THROW","ERROR_* functions, THROW vs RAISERROR, rethrow pattern, XACT_ABORT and XACT_STATE.","2 hrs"),
 (3,"WED","Transactions and isolation levels","Transactions","ACID, @@TRANCOUNT and the nesting myth, savepoints, five isolation levels vs three anomalies.","2 hrs"),
 (4,"THU","Locking, deadlocks and triggers","Locks · Triggers","Lock modes, finding blockers, deadlock graphs and retries, AFTER/INSTEAD OF triggers.","2 hrs"),
 (5,"FRI","TVPs, temp tables and table variables","TVPs &amp; temp tables","Table types, READONLY, calling from C#, #t vs @t differences, SELECT INTO.","2 hrs"),
 (6,"SAT","Sales schema + report procedures","Project: sales procs","Customers/orders/products schema, OUTPUT totals, pagination, THROW validation, multi-result procs.","4 hrs"),
 (7,"SUN","usp_PlaceOrder: atomic ordering","Project: place order","TVP-fed transactional proc, stock locking, failure tests, deadlock retry wrapper, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week13.html", 13,
      "Week 13 — Programmability and transactions", "Phase 2", "~18 hrs",
      ["Phase 2 · Week 13 of 74",".NET 8 LTS / 9","SQL Server 2022","~18 hrs","Sales procs"],
      "This week T-SQL grows up: logic moves into stored procedures with real error handling, and you learn what actually happens when two sessions touch the same rows — transactions, isolation levels, locks and deadlocks. The weekend project builds a sales schema with report procedures, then a fully transactional, TVP-fed order-placing procedure that survives everything you throw at it.",
      cards, days)
print("built")
