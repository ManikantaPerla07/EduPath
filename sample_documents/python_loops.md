# Python Loops

## 1. What is a loop?

A loop repeats a block of code. Loops are useful when the same operation must be performed for several values or until a condition changes.

Python provides two main loop statements:

- `for`: Iterates over items in an iterable, such as a range or list.
- `while`: Repeats while a condition remains true.

## 2. The for loop

A `for` loop processes each item in a sequence.

```python
for fruit in ["apple", "banana", "mango"]:
    print(fruit)
```

Output:

```text
apple
banana
mango
```

The loop variable receives one item at a time.

## 3. Using range()

The `range()` function generates a sequence of integers.

- `range(stop)`: Starts at zero and stops before `stop`.
- `range(start, stop)`: Starts at `start` and stops before `stop`.
- `range(start, stop, step)`: Uses the specified step.

Example:

```python
for number in range(2, 8, 2):
    print(number)
```

Output:

```text
2
4
6
```

The stop value 8 is excluded. A step can also be negative when the start and stop values are chosen appropriately.

## 4. The while loop

A `while` loop repeats as long as its condition is true.

```python
count = 1

while count <= 3:
    print(count)
    count += 1
```

Output:

```text
1
2
3
```

The variable changes during each iteration. When count becomes 4, the condition is false and the loop stops.

Always make sure a `while` loop can eventually reach a false condition. Otherwise, it may become an infinite loop.

## 5. break

The `break` statement immediately exits the nearest enclosing loop.

```python
for number in range(1, 6):
    if number == 4:
        break
    print(number)
```

Output:

```text
1
2
3
```

The value 4 is not printed because the loop exits before reaching the print statement.

## 6. continue

The `continue` statement skips the remaining statements in the current iteration and moves to the next iteration.

```python
for number in range(1, 6):
    if number == 3:
        continue
    print(number)
```

Output:

```text
1
2
4
5
```

Unlike `break`, `continue` does not end the loop.

## 7. Nested loops

A loop inside another loop is called a nested loop. The inner loop runs completely for each iteration of the outer loop.

```python
for row in range(1, 3):
    for column in range(1, 4):
        print(row, column)
```

Output:

```text
1 1
1 2
1 3
2 1
2 2
2 3
```

If the outer loop runs 2 times and the inner loop runs 3 times for each outer iteration, the print statement runs 6 times.

## 8. Looping through collections

```python
numbers = [10, 20, 30]
total = 0

for number in numbers:
    total += number

print(total)
```

Output: `60`.

A loop can also process dictionary keys, string characters and other iterable objects.

## 9. Common mistakes

- Forgetting to update the condition variable in a `while` loop.
- Assuming `range(5)` includes 5; it produces 0 through 4.
- Confusing `break` with `continue`.
- Incorrect indentation, which changes which statements belong to the loop.
- Modifying a collection while iterating over it without understanding the effect.

## 10. Practice

1. Print all numbers from 1 through 10.
2. Calculate the sum of numbers from 1 through 100.
3. Print only the even numbers from 1 through 20.
4. Count how many vowels appear in a string.
5. Use nested loops to print a three-row by four-column pattern.
6. Write a `while` loop that keeps asking for a number until the user enters zero.

## Key points

Use `for` when iterating over a known sequence or collection. Use `while` when repetition depends on a condition. Use `break` to exit a loop and `continue` to skip one iteration.
