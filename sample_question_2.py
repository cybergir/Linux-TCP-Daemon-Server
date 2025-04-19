def reverse_words(sentence):
    words = sentence.split()
    reversed_words = [word[::-1] for word in words]
    return " ".join(reversed_words)

sentence = input("Enter a sentence: ")
print("Reversed sentence: ", reverse_words(sentence))