# Python Variables and Data Types

## 1. What is a variable?

A variable is a name that refers to a value in a program. In Python, a variable is created when a value is assigned.

```python
name = "Alex"
age = 20
height = 170.0
```

The names `name`, `age` and `height` refer to different values.

## 2. Python data types

Python includes several built-in data types.

| Type | Purpose | Example |
|---|---|---|
| `int` | Whole numbers | `10`, `-4` |
| `float` | Decimal numbers | `3.14`, `170.0` |
| `str` | Text | `"Hello Python"` |
| `bool` | True or false values | `True`, `False` |

Example:

```python
age = 20
height = 170.0
name = "Alex"
is_student = True

print(type(age).__name__)
print(type(height).__name__)
print(type(name).__name__)
print(type(is_student).__name__)
```

Output:

```text
int
float
str
bool
```

## 3. Checking data types

Python provides the `type()` function to identify the type of a value.

```python
value = 25
print(type(value))
```

Output:

```text
<class 'int'>
```

The value `25` is an integer. The value `25.0` is a floating-point number, while `"25"` is a string.

## 4. Dynamic typing

Python is dynamically typed. You do not need to declare a variable's data type explicitly. A variable can later refer to a value of a different type.

```python
value = 10
print(type(value).__name__)

value = "Python"
print(type(value).__name__)
```

Output:

```text
int
str
```

Reassigning the variable changes the value it refers to. It does not change the type of the original integer object.

## 5. Variable naming and common mistakes

Use descriptive names that explain what a value represents.

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
