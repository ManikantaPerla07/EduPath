# Python Conditional Statements

## 1. Why do programs need conditions?

A program often needs to choose what to do based on a value. Conditional statements let Python execute different blocks depending on whether an expression is true or false.

Example:

```python
temperature = 32

if temperature > 30:
    print("It is hot")
```

Output:

```text
It is hot
```

The indented statement runs because the condition `temperature > 30` evaluates to `True`.

## 2. The if statement

The `if` statement runs its block only when its condition is true.

```python
age = 20

if age >= 18:
    print("Adult")
```

Important syntax rules:

- Write a colon after the condition.
- Indent the statements inside the block consistently.
- Python uses indentation to identify the block.

## 3. The if-else statement

Use `else` when the program needs one action for a true condition and another action for a false condition.

```python
number = 7

if number % 2 == 0:
    print("Even")
else:
    print("Odd")
```

Output: `Odd`.

The `else` block does not have its own condition. It runs when the preceding `if` condition is false.

## 4. The if-elif-else statement

Use `elif` to test additional conditions in order. Python executes the first matching branch and skips the remaining branches.

```python
marks = 82

if marks >= 90:
    print("Grade A")
elif marks >= 75:
    print("Grade B")
elif marks >= 60:
    print("Grade C")
else:
    print("Needs improvement")
```

Output: `Grade B`.

The order matters. Put more specific or higher-threshold conditions before broader conditions. If `marks >= 60` were checked first, a score of 82 would match it before reaching the higher grade.

## 5. Combining conditions

Use logical operators to combine conditions.

```python
age = 22
has_ticket = True

if age >= 18 and has_ticket:
    print("Entry allowed")
else:
    print("Entry denied")
```

Output: `Entry allowed`.

Use `and` when every condition must be true. Use `or` when at least one condition is enough.

## 6. Nested conditions

A conditional can contain another conditional.

```python
number = 12

if number > 0:
    if number % 2 == 0:
        print("Positive even number")
    else:
        print("Positive odd number")
else:
    print("Zero or negative")
```

Output: `Positive even number`.

Nested conditions are useful, but too many levels can make code difficult to follow. Consider combining simple conditions with `and` or `or` when that makes the logic clearer.

## 7. Truth values and empty values

Conditions do not always need an explicit comparison. Python treats some values as false in a condition, including:

- `False`
- `None`
- Numeric zero, such as `0`
- Empty strings, such as `""`
- Empty collections, such as `[]` and `{}`

Example:

```python
name = ""

if name:
    print("Name provided")
else:
    print("Name is empty")
```

Output: `Name is empty`.

For beginner programs, explicit comparisons can sometimes be easier to understand. Use the form that makes the intention clearest.

## 8. Common mistakes

- Forgetting the colon after `if`, `elif` or `else`.
- Using inconsistent indentation.
- Writing `=` instead of `==` for comparison.
- Placing a broad condition before a more specific condition.
- Using separate `if` statements when only one branch should run; an `if-elif-else` chain may be more suitable.

## 9. Practice

1. Write a program that prints whether a number is positive, negative or zero.
2. Write a program that prints the largest of two numbers.
3. Write a grade calculator using `if`, `elif` and `else`.
4. Check whether a number is between 10 and 50 inclusive.
5. Predict the output when `score = 70` and the first condition is `score > 70`, followed by `score >= 70`.

## Key points

Conditional statements control the path of a program. Choose between `if`, `if-else`, and `if-elif-else` based on the number of decisions, and keep conditions and indentation clear.
