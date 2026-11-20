export const SQL_DEMOS = [
  { badge: "SQL 1", label: "Selection (Filter Pushdown)", query: "SELECT *\nFROM Student\nWHERE age > 23\nLIMIT 10;" },
  { badge: "SQL 2", label: "Projection & Pruning", query: "SELECT name, cgpa\nFROM Student\nWHERE branch = 'ECE'\nLIMIT 10;" },
  { badge: "SQL 3", label: "Conjunctive Predicates", query: "SELECT name, age\nFROM Student\nWHERE age > 23 AND branch = 'ECE'\nLIMIT 10;" },
  { badge: "SQL 4", label: "2-Table JOIN (Hash Join)", query: "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nLIMIT 10;" },
  { badge: "SQL 5", label: "JOIN + Multi Filtering", query: "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nWHERE s.age > 23 AND d.dept_name = 'Computer Science'\nLIMIT 10;" },
  { badge: "SQL 6", label: "3-Way JOIN", query: "SELECT s.name, c.course_name, e.marks\nFROM Student s\nINNER JOIN Enrollment e\nON s.student_id = e.student_id\nINNER JOIN Course c\nON e.course_id = c.course_id\nWHERE e.marks > 80\nLIMIT 10;" },
  { badge: "SQL 7", label: "Sort & Top-K", query: "SELECT name, cgpa\nFROM Student\nORDER BY cgpa DESC\nLIMIT 10;" },
];

export const NL_DEMOS = [
  { badge: "NL 1", label: "Students age>23 in ECE", query: "List out all the students above age 23 whose branch is ECE." },
  { badge: "NL 2", label: "CSE names & CGPA", query: "Show the names and CGPA of all CSE students." },
  { badge: "NL 3", label: "Scored > 80 marks", query: "Find students who scored more than 80 marks in their courses." },
  { badge: "NL 4", label: "Top 10 by CGPA", query: "List the top 10 students based on CGPA." },
];

export const ERR_DEMOS = [
  { badge: "ERR 1", label: "Lexical Error (# char)", query: "SELECT name # age FROM Student;" },
  { badge: "ERR 2", label: "Syntax Error (No FROM)", query: "SELECT FROM Student;" },
  { badge: "ERR 3", label: "Semantic Error (Bad col)", query: "SELECT unknown_column FROM Student;" },
];
