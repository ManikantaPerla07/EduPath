# Python Lists and Tuples

## 1. Sequence collections

Lists and tuples store multiple values in a specific order. Both support indexing, slicing and iteration.

The main difference is mutability:

- A list is mutable; its contents can be changed.
- A tuple is immutable; its structure cannot be changed after creation.

## 2. Creating lists

Use square brackets to create a list.

```python
numbers = [10, 20, 30, 40]
names = ["Asha", "Ravi", "Mina"]
mixed = [10, "Python", True]
```

Lists can contain values of different types, although lists containing related values are often easier to work with.

## 3. Indexing and negative indexing

List indexes start at zero.

```python
colors = ["red", "green", "blue"]
print(colors[0])
print(colors[2])
print(colors[-1])
```

Output:

```text
red
blue
blue
```

Negative indexes count from the end. Index `-1` refers to the last item.

An index outside the valid range raises `IndexError`.

## 4. Slicing

Slicing extracts a portion of a sequence. The stop index is excluded.

```python
numbers = [10, 20, 30, 40, 50]
print(numbers[1:4])
print(numbers[:3])
print(numbers[2:])
```

Output:

```text
[20, 30, 40]
[10, 20, 30]
[30, 40, 50]
```

A slice may also include a step, such as `numbers[::2]`.

## 5. Modifying lists

Common list methods include:

| Method | Purpose |
|---|---|
| `append(value)` | Adds one item to the end |
| `extend(values)` | Adds items from an iterable |
| `insert(index, value)` | Inserts at a position |
| `remove(value)` | Removes the first matching value |
| `pop(index)` | Removes and returns an item |
| `sort()` | Sorts the list in place |
| `reverse()` | Reverses the list in place |
| `clear()` | Removes all items |

Example:

```python
numbers = [3, 1, 2]
numbers.append(4)
numbers.sort()
print(numbers)
```

Output: `[1, 2, 3, 4]`.

The `sort()` method changes the existing list and returns `None`. The built-in `sorted()` function returns a new sorted list.

## 6. List aliasing

Assignment does not automatically copy a list.

```python
first = [1, 2]
second = first
second.append(3)

print(first)
```

Output: `[1, 2, 3]`.

Both variables refer to the same list. A shallow copy of a simple list can be made with `first.copy()` or `first[:]`.

## 7. Creating tuples

Use parentheses or commas to create a tuple.

```python
point = (10, 20)
colors = ("red", "green", "blue")
single_item = (5,)
```

The comma is required for a one-item tuple.

Tuples support indexing and slicing, but items cannot be added, removed or reassigned.

```python
point = (10, 20)
print(point[0])
```

Output: `10`.

Trying to assign `point[0] = 99` raises `TypeError`.

## 8. Tuple unpacking

Tuple unpacking assigns individual values to variables.

```python
person = ("Anu", 21)
name, age = person

print(name)
print(age)
```

Output:

```text
Anu
21
```

The number of variables normally needs to match the number of values being unpacked.

## 9. Choosing a list or tuple

Use a list when the collection needs to change. Use a tuple when the collection represents a fixed group of values.

Both can be iterated over with a `for` loop and both can contain nested collections.

## 10. Common mistakes

- Forgetting that sequence indexes start at zero.
- Expecting the stop index in a slice to be included.
- Assigning the result of `list.sort()` to a variable.
- Assuming `second = first` creates a copy.
- Trying to modify a tuple.
- Forgetting the comma in a one-item tuple.

## 11. Practice

1. Create a list of five numbers and print its first and last values.
2. Extract the middle three values using slicing.
3. Add a value, remove a value and sort a list.
4. Explain why changing `second` can change `first` after `second = first`.
5. Create a tuple with a student's name and score, then unpack it.
6. Convert a list of repeated values into a collection of unique values using a set.

## Key points

Lists are ordered and mutable. Tuples are ordered and immutable. Understand indexing, slicing, list methods, copying and unpacking to use Python sequences safely.
