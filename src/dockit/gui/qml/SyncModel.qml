import QtQuick

// A list that is updated in place: only rows that really changed are touched, so nothing
// is rebuilt (and nothing flickers) when the program refreshes its numbers every few seconds.
ListModel {
    function sync(arr) {
        arr = arr || []
        for (var i = 0; i < arr.length; i++) {
            if (i >= count) {
                append(arr[i])
                continue
            }
            var row = get(i)
            for (var k in arr[i])
                if (row[k] !== arr[i][k])
                    setProperty(i, k, arr[i][k])
        }
        while (count > arr.length)
            remove(count - 1)
    }
}
