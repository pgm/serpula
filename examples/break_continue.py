i = 0
while i < 10:
    i += 1
    if i == 3:
        continue
    if i == 6:
        break
    print(i)

total = 0
for x in range(10):
    if x % 2 == 0:
        continue
    total += x
    if total > 15:
        break
print(total)
