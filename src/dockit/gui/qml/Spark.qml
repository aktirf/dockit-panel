import QtQuick

Canvas {
    id: c
    property var values: []
    property color lineColor: Theme.accent

    implicitHeight: 40
    onValuesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        var v = values
        if (!v || v.length < 2 || width < 4) return
        var mn = Math.min.apply(null, v)
        var mx = Math.max.apply(null, v)
        if (mx - mn < 4) {
            var mid = (mx + mn) / 2
            mn = mid - 2
            mx = mid + 2
        }
        ctx.strokeStyle = lineColor
        ctx.lineWidth = 2
        ctx.lineJoin = "round"
        ctx.lineCap = "round"
        ctx.beginPath()
        for (var i = 0; i < v.length; i++) {
            var x = 2 + i * (width - 4) / (v.length - 1)
            var y = height - 3 - (v[i] - mn) / (mx - mn) * (height - 6)
            if (i === 0) ctx.moveTo(x, y)
            else ctx.lineTo(x, y)
        }
        ctx.stroke()
    }
}
