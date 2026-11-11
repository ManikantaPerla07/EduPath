# Python Variables and Data Types

## 1. What is a variable?

A variable is a named location used to store data in a program.
In Python, variables are created when a value is assigned.

Example:

name = "Alex"
age = 20
height = 170.0

## 2. Python data types

Python supports several built-in data types.

- int: Stores whole numbers, such as 10 and 25.
- float: Stores decimal numbers, such as 3.14.
- str: Stores text, such as "Hello Python".
- bool: Stores either True or False.

## 3. Checking data types

Python provides the type() function to identify the type of a value.

Example:

age = 20
print(type(age))

Output:

<class 'int'>

## 4. Dynamic typing

Python is dynamically typed. You do not need to declare
a variable's data type explicitly.

Example:

value = 10
value = "Python"

The same variable can refer to values of different types.

## 5. Variable naming and common mistakes

Use descriptive names that explain what a value represents.

Good examples:

```python
student_name = "Alex"
total_marks = 85
is_present = True
```

Python variable names:
- Can contain letters, digits and underscores.
- Cannot start with a digit.
- Are case-sensitive, so `score` and `Score` are different names.
- Cannot be Python reserved keywords such as `if`, `for` or `class`.

Common mistakes include using a variable before assigning it, confusing a number with text, and using a reserved keyword as a variable name.

## 6. Practice

1. Create variables for a student's name, age, percentage and whether the student is active. Choose a suitable data type for each.
2. Predict the type of each value: `25`, `25.0`, `"25"` and `False`.
3. Use `type()` to display the data type of a variable.
4. Assign an integer to a variable, then assign a string to the same variable. What does this demonstrate?
5. Identify which names are valid Python variables: `student_name`, `2score`, `totalMarks` and `class`.

## Key points

Variables are names that refer to values. Python has built-in types such as `int`, `float`, `str` and `bool`, and it uses dynamic typing. Use meaningful names, understand the type of each value, and remember that assignment can change which value a variable refers to.
