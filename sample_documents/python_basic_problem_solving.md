# Basic Problem Solving with Python

## 1. A structured way to solve a problem

Programming problem solving is the process of turning a requirement into clear steps and then implementing those steps in code.

A useful beginner workflow is:

1. Understand the problem statement.
2. Identify the input and expected output.
3. Work through a small example by hand.
4. Break the task into smaller steps.
5. Write the algorithm in plain language or pseudocode.
6. Implement the solution.
7. Test normal cases and edge cases.

Do not start coding until you understand what the program is expected to do.

## 2. Identify input, processing and output

Consider the problem: determine whether a number is even or odd.

- Input: one integer.
- Processing: calculate the remainder when divided by 2.
- Output: "Even" when the remainder is zero; otherwise "Odd".

```python
number = 17

if number % 2 == 0:
    result = "Even"
else:
    result = "Odd"

print(result)
```

Output: `Odd`.

## 3. Trace a program manually

Tracing means following a program one statement at a time and recording how variable values change.

```python
total = 0

for number in [2, 4, 6]:
    total += number

print(total)
```

Trace:

| Iteration | number | total after addition |
|---|---:|---:|
| Start | — | 0 |
| 1 | 2 | 2 |
| 2 | 4 | 6 |
| 3 | 6 | 12 |

Output: `12`.

Tracing is useful when debugging loops, conditions and expressions.

## 4. Find the largest value

A simple approach is to keep track of the largest value seen so far.

```python
numbers = [4, 9, 2, 7]
largest = numbers[0]

for number in numbers:
    if number > largest:
        largest = number

print(largest)
```

Output: `9`.

This example assumes the list is not empty. Decide what the program should do for an empty list before using this algorithm in a real application.

## 5. Count occurrences with a dictionary

A dictionary can keep a count for each value.

```python
values = ["a", "b", "a", "c", "b", "a"]
frequency = {}

for value in values:
    frequency[value] = frequency.get(value, 0) + 1

print(frequency)
```

The counts are 3 for `a`, 2 for `b` and 1 for `c`. Dictionary display order follows insertion order.

This pattern is useful for counting words, characters and repeated values.

## 6. Remove duplicates while preserving order

A set can check whether a value has already appeared. A list can preserve the first-occurrence order.

```python
numbers = [4, 2, 4, 3, 2]
unique = []
seen = set()

for number in numbers:
    if number not in seen:
        unique.append(number)
        seen.add(number)

print(unique)
```

Output: `[4, 2, 3]`.

The list stores the answer in the original order. The set makes membership checks straightforward.

## 7. Break a problem into functions

A long problem is easier to understand when divided into smaller functions.

```python
def is_even(number):
    return number % 2 == 0


def count_even(numbers):
    count = 0

    for number in numbers:
        if is_even(number):
            count += 1

    return count


print(count_even([1, 2, 3, 4, 6]))
```

Output: `3`.

The `is_even()` function handles one small task, and `count_even()` reuses it.

## 8. Test edge cases

An edge case is an input near the boundary of what the problem allows. Test cases should include:

- An empty list, if empty input is allowed.
- A list with one element.
- Repeated values.
- Negative numbers and zero.
- Already sorted input.
- Input containing the minimum or maximum allowed value.

For example, the largest-value algorithm must define how an empty list is handled. Do not assume every input is non-empty unless the problem statement guarantees it.

## 9. Debugging approach

When output is incorrect:

1. Re-read the expected input and output.
2. Check variable initialization.
3. Trace each loop iteration.
4. Check condition boundaries such as `<` versus `<=`.
5. Test a small input where the expected answer is easy to calculate.
6. Read the full error message if Python raises an exception.

Avoid changing multiple parts of a program at once. Make one clear change and test it.

## 10. Practice

1. Find the sum of all numbers in a list.
2. Find the smallest value in a non-empty list.
3. Count how many numbers are even.
4. Check whether a word is a palindrome.
5. Count the frequency of each character in a string.
6. Remove duplicates from a list while preserving order.
7. Write a function that returns the second largest distinct value, and decide what should happen when fewer than two distinct values exist.

## Key points

Start with the input and expected output, build a simple algorithm, trace it, implement it and test edge cases. Lists, dictionaries, sets, loops and functions are practical building blocks for beginner problem solving.
