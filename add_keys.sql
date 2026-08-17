-- Run this AFTER clean_and_load.py has created and populated all 7 tables.
-- Adds primary keys and foreign keys so the tables behave as a real
-- relational model instead of 7 loose tables.

USE roblox_workforce_db;

-- Primary keys
ALTER TABLE department            ADD PRIMARY KEY (department_code);
ALTER TABLE employee              ADD PRIMARY KEY (EmployeeID);
ALTER TABLE education              ADD PRIMARY KEY (employee_id);
ALTER TABLE health                 ADD PRIMARY KEY (`Employee ID`);
ALTER TABLE finance                ADD PRIMARY KEY (StaffID);
ALTER TABLE employee_performance   ADD PRIMARY KEY (EmployeeID, Year);

-- department_performance already has a unique row ID (DepartmentId, 1-40,
-- one per department-year combination) - that alone is the primary key
ALTER TABLE department_performance ADD PRIMARY KEY (DepartmentId);

-- department_name needs a UNIQUE constraint before anything can reference
-- it as a foreign key target (only PRIMARY/UNIQUE keys can be FK targets)
ALTER TABLE department ADD CONSTRAINT uq_department_name UNIQUE (department_name);

-- Foreign keys linking everything back to the Employee hub and Department
ALTER TABLE employee
  ADD CONSTRAINT fk_employee_department
  FOREIGN KEY (`Department Code`) REFERENCES department(department_code);

ALTER TABLE education
  ADD CONSTRAINT fk_education_employee
  FOREIGN KEY (employee_id) REFERENCES employee(EmployeeID);

ALTER TABLE health
  ADD CONSTRAINT fk_health_employee
  FOREIGN KEY (`Employee ID`) REFERENCES employee(EmployeeID);

ALTER TABLE finance
  ADD CONSTRAINT fk_finance_employee
  FOREIGN KEY (StaffID) REFERENCES employee(EmployeeID);

ALTER TABLE employee_performance
  ADD CONSTRAINT fk_empperf_employee
  FOREIGN KEY (EmployeeID) REFERENCES employee(EmployeeID);

-- department_performance links to Department by NAME (e.g. "Finance
-- Department"), not by code - confirmed against the actual dataset
ALTER TABLE department_performance
  ADD CONSTRAINT fk_deptperf_department
  FOREIGN KEY (Department) REFERENCES department(department_name);
