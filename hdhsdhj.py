def catchingOdd(n):
    result = []
    seen = []
    for i in L:
        if i % 2 != 0:
            result.append(i)
        if i in result and i not in seen:
            seen.append(i)
            result.remove(i)
    return result


L = [1,2,2,3,4,5,5,7,9,10]
print(catchingOdd(L))
