# Python Operators and Expressions

## 1. What is an operator?

An operator performs an operation on one or more values. The values are called operands, and an expression combines values and operators to produce a result.

```python
total = 10 + 5
print(total)
```

Output:

```text
15
```

## 2. Arithmetic operators

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `+` | Addition | `7 + 2` | `9` |
| `-` | Subtraction | `7 - 2` | `5` |
| `*` | Multiplication | `7 * 2` | `14` |
| `/` | Division | `7 / 2` | `3.5` |
| `//` | Floor division | `7 // 2` | `3` |
| `%` | Remainder | `7 % 2` | `1` |
| `**` | Exponentiation | `2 ** 3` | `8` |

Division with `/` produces a floating-point result, even when the division is exact.

```python
print(8 / 2)
print(8 // 2)
print(9 % 2)
```

Output:

```text
4.0
4
1
```

Floor division rounds down to the nearest whole number. For negative values, this means toward negative infinity:

```python
print(-7 // 2)
```

Output: `-4`.

## 3. Comparison operators

Comparison operators compare two values and produce either `True` or `False`.

| Operator | Meaning |
|---|---|
| `==` | Equal to |
| `!=` | Not equal to |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal to |
| `<=` | Less than or equal to |

Example:

```python
age = 21
print(age >= 18)
print(age == 20)
print(age != 18)
```

Output:

```text
True
False
True
```

Do not confuse `=` with `==`. A single equals sign assigns a value. A double equals sign compares values.

## 4. Logical operators

Logical operators combine or reverse Boolean conditions.

- `and`: True only when both conditions are True.
- `or`: True when at least one condition is True.
- `not`: Reverses a Boolean result.

```python
age = 22
has_id = True

print(age >= 18 and has_id)
print(age < 18 or has_id)
print(not has_id)
```

Output:

```text
True
True
False
```

Python evaluates `and` and `or` using short-circuit evaluation. It may skip evaluating the right-hand operand when the left-hand operand already determines the result.

## 5. Assignment operators

Assignment operators update a variable.

```python
score = 10
score += 5
score -= 2
score *= 2
print(score)
```

Output: `26`.

Common forms include `+=`, `-=`, `*=`, `/=`, `//=`, `%=` and `**=`.

## 6. Operator precedence

When an expression contains multiple operators, Python follows precedence rules. Parentheses can make the intended order clear.

```python
print(2 + 3 * 4)
print((2 + 3) * 4)
print(2 ** 3 ** 2)
```

Output:

```text
14
20
512
```

Exponentiation is evaluated from right to left, so the last expression is interpreted as `2 ** (3 ** 2)`.

A useful beginner-level order is:

1. Parentheses.
2. Exponentiation.
3. Multiplication, division, floor division and remainder.
4. Addition and subtraction.
5. Comparisons.
6. `not`.
7. `and`.
8. `or`.

Use parentheses when an expression is difficult to read.

## 7. Common mistakes

- Using `=` instead of `==` in a condition.
- Expecting `/` to return an integer.
- Assuming `//` always truncates toward zero.
- Forgetting operator precedence.
- Using `and` when either condition should be sufficient; that case usually needs `or`.

## 8. Practice

1. What are the results of `17 // 5` and `17 % 5`?
2. What does `3 ** 2 ** 2` evaluate to?
3. Write a condition that checks whether `marks` is at least 40 and attendance is at least 75.
4. Start with `count = 4`, apply `count *= 3`, then `count += 2`. What is the final value?
5. Explain the difference between `and` and `or` using two Boolean variables.

## Key points

Operators let Python programs calculate values, compare data and combine conditions. Understand the result type of each operation and use parentheses to make complex expressions easy to read.
