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
