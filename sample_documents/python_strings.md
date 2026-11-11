# Python Strings

## 1. What is a string?

A string is a sequence of characters used to represent text. Strings can be written with single quotes, double quotes or triple quotes.

```python
first = 'Hello'
second = "Python"
message = """This is
multiple lines."""
```

Single and double quotes are interchangeable for ordinary strings. Triple quotes are useful for multi-line text and docstrings.

## 2. String indexing

Strings use zero-based indexing.

```python
word = "Python"
print(word[0])
print(word[3])
print(word[-1])
```

Output:

```text
P
h
n
```

An index outside the valid range raises `IndexError`.

## 3. String slicing

Slicing extracts a part of a string. The stop index is excluded.

```python
word = "Python"
print(word[1:4])
print(word[:2])
print(word[2:])
```

Output:

```text
yth
Py
thon
```

A step can be included. For example, `word[::2]` selects every second character.

## 4. Strings are immutable

A string cannot be changed in place. Methods that appear to modify a string return a new string.

```python
word = "cat"
new_word = word.replace("c", "b")

print(word)
print(new_word)
```

Output:

```text
cat
bat
```

The original string remains unchanged.

## 5. Useful string methods

| Method | Purpose |
|---|---|
| `lower()` | Converts letters to lowercase |
| `upper()` | Converts letters to uppercase |
| `title()` | Capitalizes words |
| `strip()` | Removes surrounding whitespace |
| `replace(old, new)` | Returns a string with replacements |
| `split(separator)` | Splits a string into a list |
| `join(iterable)` | Joins strings using a separator |
| `startswith(prefix)` | Checks the beginning |
| `endswith(suffix)` | Checks the ending |
| `find(substring)` | Returns the first matching index or -1 |

Example:

```python
text = "  Learn Python  "
cleaned = text.strip().lower()
print(cleaned)
```

Output: `learn python`.

## 6. split() and join()

`split()` divides a string into a list.

```python
sentence = "Python is useful"
words = sentence.split()
print(words)
```

Output: `['Python', 'is', 'useful']`.

`join()` combines an iterable of strings.

```python
words = ["Python", "is", "useful"]
sentence = " ".join(words)
print(sentence)
```

Output: `Python is useful`.

The separator is written before `join()`. The items being joined must be strings.

## 7. String formatting

An f-string inserts expressions into a string using curly braces.

```python
name = "Asha"
score = 92
print(f"{name} scored {score} marks.")
```

Output: `Asha scored 92 marks.`.

F-strings are useful for readable messages and formatted values.

## 8. Escape characters

Escape sequences represent special characters.

- `\n`: New line.
- `\t`: Tab.
- `\\`: Backslash.
- `\'`: Single quote.
- `\"`: Double quote.

Example:

```python
print("Python\nProgramming")
```

Output:

```text
Python
Programming
```

## 9. Common mistakes

- Trying to assign to an individual character in a string.
- Forgetting that the slice stop index is excluded.
- Assuming `replace()` changes the original string.
- Using `join()` with non-string values.
- Confusing `find()` returning -1 with an exception.
- Forgetting to remove extra whitespace before comparing user-entered text.

## 10. Practice

1. Print the first and last character of a word.
2. Reverse a string using slicing.
3. Count the number of vowels in a string.
4. Convert a sentence to lowercase and remove surrounding spaces.
5. Split a sentence into words and join them with hyphens.
6. Use an f-string to display a person's name and age.

## Key points

Strings are immutable sequences of characters. Learn indexing, slicing, methods, formatting and escape sequences to process text correctly.
