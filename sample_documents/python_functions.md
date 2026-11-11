# Python Functions

## 1. What is a function?

A function is a reusable block of code that performs a task. Functions help organize programs, avoid repeating logic and make code easier to test.

Python provides built-in functions such as `print()`, `len()` and `type()`. You can also define your own functions.

## 2. Defining and calling a function

Use the `def` keyword to define a function.

```python
def greet():
    print("Hello, Python!")

greet()
```

Output: `Hello, Python!`.

The function body is indented. Defining a function does not execute its body; calling the function does.

## 3. Parameters and arguments

Parameters are names in the function definition. Arguments are the actual values supplied when calling the function.

```python
def greet(name):
    print("Hello,", name)

greet("Ravi")
```

Output: `Hello, Ravi`.

A function can accept multiple parameters.

```python
def add(first, second):
    print(first + second)

add(4, 6)
```

Output: `10`.

## 4. Return values

The `return` statement sends a result back to the caller and ends the function call.

```python
def square(number):
    return number * number

result = square(5)
print(result)
```

Output: `25`.

Do not confuse `print()` and `return`:

- `print()` displays information.
- `return` gives a value back so the caller can store it, use it in an expression or return it again.

If a function reaches the end without an explicit return statement, Python returns `None`.

## 5. Default and keyword arguments

A parameter can have a default value.

```python
def greet(name, message="Welcome"):
    print(message, name)

greet("Anu")
greet("Anu", "Good morning")
```

Output:

```text
Welcome Anu
Good morning Anu
```

Arguments can also be passed by parameter name:

```python
def describe(name, age):
    print(name, age)

describe(age=20, name="Anu")
```

Output: `Anu 20`.

## 6. Local and global variables

A variable created inside a function is normally local to that function.

```python
def show_value():
    message = "Inside function"
    print(message)

show_value()
```

The local variable `message` is not available outside the function. Prefer passing values as parameters and returning results instead of relying on global variables.

## 7. Mutable default argument warning

Default argument expressions are evaluated when the function is defined, not each time it is called. Avoid using a mutable list or dictionary as a default value when you expect a fresh object for every call.

Problematic pattern:

```python
def add_item(item, items=[]):
    items.append(item)
    return items
```

The same list is reused between calls. A safer pattern is:

```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

Now a new list is created whenever no list is supplied.

## 8. Docstrings and readable functions

A docstring describes what a function does.

```python
def calculate_area(length, width):
    """Return the area of a rectangle."""
    return length * width
```

Keep a function focused on one clear task. Use descriptive names and return values that callers can use.

## 9. Common mistakes

- Defining a function but never calling it.
- Forgetting to pass a required argument.
- Expecting `print()` to return a useful value.
- Forgetting to return a calculated result.
- Using local variables outside their function.
- Using mutable default arguments unintentionally.

## 10. Practice

1. Write a function that returns the larger of two numbers.
2. Write a function that checks whether a number is even.
3. Write a function that accepts a name and returns a greeting string.
4. Write a function that calculates the area of a circle using a radius.
5. Write a function with a default argument for a country name.
6. Explain why `return` is different from `print()`.

## Key points

Functions make programs modular and reusable. Learn how to define and call functions, pass arguments, return values and choose safe default arguments.
