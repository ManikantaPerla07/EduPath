# Python Dictionaries and Sets

## 1. Dictionaries

A dictionary stores data as key-value pairs. Each key is used to access its corresponding value.

Create a dictionary with curly braces:

```python
student = {
    "name": "Asha",
    "age": 20,
    "course": "Python"
}

print(student["name"])
```

Output: `Asha`.

Dictionary keys must be unique. If the same key is assigned again, its value is replaced.

## 2. Accessing dictionary values

Square brackets access a key directly. If the key does not exist, Python raises `KeyError`.

The `get()` method can return a default value when a key is missing.

```python
student = {"name": "Asha"}
print(student.get("name"))
print(student.get("score", 0))
```

Output:

```text
Asha
0
```

Use square brackets when a missing key should be treated as an error. Use `get()` when a default is appropriate.

## 3. Adding, changing and removing entries

```python
student = {"name": "Asha"}
student["age"] = 20
student["name"] = "Anu"
student.pop("age")

print(student)
```

Output: `{'name': 'Anu'}`.

Useful dictionary methods include:

- `keys()`: Returns the keys.
- `values()`: Returns the values.
- `items()`: Returns key-value pairs.
- `update()`: Adds or updates entries.
- `pop(key)`: Removes a key and returns its value.
- `clear()`: Removes every entry.

## 4. Iterating over a dictionary

```python
scores = {"Asha": 90, "Ravi": 85}

for name, score in scores.items():
    print(name, score)
```

Output:

```text
Asha 90
Ravi 85
```

Dictionaries preserve insertion order in modern Python. Use `items()` when both the key and value are needed.

## 5. Sets

A set is a collection of unique elements. It is useful for removing duplicates and performing membership tests.

```python
numbers = {1, 2, 2, 3, 3}
print(numbers)
print(len(numbers))
```

The set contains the unique values 1, 2 and 3, so its length is 3. Do not rely on a particular display order for set elements.

Create an empty set with `set()`. Empty curly braces `{}` create an empty dictionary, not an empty set.

## 6. Set operations

Common set operations include:

- Union: combines elements from both sets using `|` or `union()`.
- Intersection: keeps common elements using `&` or `intersection()`.
- Difference: keeps elements in the first set but not the second using `-` or `difference()`.
- Symmetric difference: keeps elements that appear in exactly one set using `^`.

Example:

```python
python_students = {"Asha", "Ravi", "Mina"}
java_students = {"Ravi", "Kiran"}

print(python_students & java_students)
print(python_students | java_students)
print(python_students - java_students)
```

The intersection is `{'Ravi'}`; the union contains all four names; the difference contains the names found only in the Python set. Set display order is not guaranteed.

## 7. Membership testing

The `in` operator checks whether a key or element exists.

```python
student = {"name": "Asha", "age": 20}
print("name" in student)
print("Asha" in student)

numbers = {10, 20, 30}
print(20 in numbers)
```

Output:

```text
True
False
True
```

For a dictionary, `in` checks keys by default, not values.

## 8. Choosing the right collection

- Use a dictionary when values need to be looked up by keys.
- Use a set when uniqueness and membership testing are important.
- Use a list when order and repeated values matter.
- Use a tuple when a fixed group of values is appropriate.

## 9. Common mistakes

- Assuming a dictionary key lookup and value lookup are the same.
- Using `{}` when an empty set is required.
- Expecting sets to preserve display order.
- Trying to use a mutable list or dictionary as a set element.
- Assuming duplicate dictionary keys are stored separately.

## 10. Practice

1. Create a dictionary containing a product name and price. Update the price.
2. Use `get()` to read a key that might be missing.
3. Count the frequency of each character in a string with a dictionary.
4. Remove duplicates from a list using a set.
5. Find common elements between two sets.
6. Explain what `"name" in student` checks when student is a dictionary.

## Key points

Dictionaries map keys to values. Sets store unique elements. Both are useful for fast lookups and for organizing data around membership or relationships.
