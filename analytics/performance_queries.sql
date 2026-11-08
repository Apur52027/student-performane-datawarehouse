-- Student Performance Data Warehouse - analytics queries
-- Each query starts with `-- name: <id>`; filters use :dept and :semester (NULL = all).

-- name: kpi_summary
-- Headline numbers for the selected filters
SELECT COUNT(DISTINCT f.student_key) AS total_students,
       COUNT(*)                      AS total_enrollments,
       ROUND(AVG(f.total_marks), 2)  AS avg_marks,
       ROUND(SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours), 2) AS avg_cgpa,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate,
       ROUND(AVG(f.attendance_pct), 1) AS avg_attendance
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester);

-- name: dept_performance
-- Performance by department
SELECT d.dept_name AS department,
       COUNT(DISTINCT f.student_key) AS students,
       ROUND(AVG(f.total_marks), 2)  AS avg_marks,
       ROUND(SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours), 2) AS avg_cgpa,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate,
       ROUND(AVG(f.attendance_pct), 1) AS avg_attendance
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY d.dept_name
ORDER BY avg_marks DESC;

-- name: semester_trend
-- Trend across semesters (semester filter ignored)
SELECT s.semester_name AS semester,
       COUNT(*) AS enrollments,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours), 2) AS avg_cgpa,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
GROUP BY s.semester_key, s.semester_name, s.semester_order
ORDER BY s.semester_order;

-- name: grade_distribution
-- How many of each grade
SELECT f.grade AS grade, COUNT(*) AS count
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY f.grade
ORDER BY MAX(f.grade_point) DESC;

-- name: top_students
-- Top 10 students by CGPA
SELECT st.student_id, st.student_name, d.dept_name AS department,
       COUNT(*) AS courses,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours), 2) AS cgpa,
       ROUND(AVG(f.attendance_pct), 1) AS avg_attendance
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY st.student_key, d.dept_name
ORDER BY cgpa DESC, avg_marks DESC
LIMIT 10;

-- name: at_risk_students
-- Students with low CGPA, low attendance or repeated failures
SELECT st.student_id, st.student_name, d.dept_name AS department,
       ROUND(SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours), 2) AS cgpa,
       ROUND(AVG(f.attendance_pct), 1) AS avg_attendance,
       SUM(1 - f.is_pass) AS failed_courses
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY st.student_key, d.dept_name
HAVING SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours) < 2.5
    OR AVG(f.attendance_pct) < 75
    OR SUM(1 - f.is_pass) >= 2
ORDER BY cgpa ASC, failed_courses DESC
LIMIT 25;

-- name: teacher_performance
-- Results by teacher
SELECT t.teacher_name AS teacher, d.dept_name AS department,
       COUNT(DISTINCT f.course_key) AS courses_taught,
       COUNT(*) AS enrollments,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY t.teacher_key, d.dept_name
ORDER BY avg_marks DESC;

-- name: course_difficulty
-- 10 hardest courses (highest fail rate)
SELECT c.course_code, c.course_name, d.dept_name AS department,
       COUNT(*) AS enrollments,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(100.0 * SUM(1 - f.is_pass) / COUNT(*), 1) AS fail_rate
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY c.course_key, d.dept_name
ORDER BY fail_rate DESC, avg_marks ASC
LIMIT 10;

-- name: attendance_impact
-- Marks and pass rate by attendance band
SELECT CASE WHEN f.attendance_pct < 60 THEN 'Below 60%'
            WHEN f.attendance_pct < 75 THEN '60-74%'
            WHEN f.attendance_pct < 90 THEN '75-89%'
            ELSE '90%+' END AS attendance_band,
       COUNT(*) AS enrollments,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY attendance_band
ORDER BY MIN(f.attendance_pct);

-- name: study_hours_impact
-- Marks by weekly study hours
SELECT CASE WHEN f.study_hours < 8  THEN 'Under 8 hrs'
            WHEN f.study_hours < 15 THEN '8-14 hrs'
            WHEN f.study_hours < 22 THEN '15-21 hrs'
            ELSE '22+ hrs' END AS study_band,
       COUNT(*) AS enrollments,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY study_band
ORDER BY MIN(f.study_hours);

-- name: gender_comparison
-- Performance by gender
SELECT st.gender AS gender,
       COUNT(DISTINCT f.student_key) AS students,
       ROUND(AVG(f.total_marks), 2) AS avg_marks,
       ROUND(SUM(f.grade_point * c.credit_hours) / SUM(c.credit_hours), 2) AS avg_cgpa,
       ROUND(100.0 * SUM(f.is_pass) / COUNT(*), 1) AS pass_rate
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key = f.student_key
JOIN dim_course     c  ON c.course_key   = f.course_key
JOIN dim_teacher    t  ON t.teacher_key  = f.teacher_key
JOIN dim_department d  ON d.dept_key     = f.dept_key
JOIN dim_semester   s  ON s.semester_key = f.semester_key
WHERE (:dept IS NULL OR d.dept_name = :dept)
  AND (:semester IS NULL OR s.semester_name = :semester)
GROUP BY st.gender
ORDER BY avg_marks DESC;
