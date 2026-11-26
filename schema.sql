CREATE TABLE IF NOT EXISTS students (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    roll text NOT NULL,
    name text NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS students_roll_lower ON students (lower(roll));
CREATE TABLE IF NOT EXISTS attendance (
    day date NOT NULL,
    student_id integer NOT NULL REFERENCES students(id),
    status text NOT NULL CHECK (status IN ('Present','Absent')),
    PRIMARY KEY(day,student_id)
);
