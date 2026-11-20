import QtQuick

Canvas {
    id: c
    property var values: []
    property color lineColor: Theme.accent
    property bool showBounds: false
    property string unit: ""

    implicitHeight: 40
    onValuesChanged: requestPaint()
    onLineColorChanged: requestPaint()
    onShowBoundsChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        var v = values
        if (!v || v.length < 2 || width < 8 || height < 8) return
        var rawMin = Math.min.apply(null, v)
        var rawMax = Math.max.apply(null, v)
        var mn = rawMin
        var mx = rawMax
        if (mx - mn < 4) {
            var mid = (mx + mn) / 2
            mn = mid - 2
            mx = mid + 2
        }
        var padLeft = showBounds ? 34 : 4
        var padRight = 6
        var padTop = 6
        var padBot = 6
        var plotW = Math.max(4, width - padLeft - padRight)
        var pts = []
        for (var i = 0; i < v.length; i++) {
            var x = padLeft + i * plotW / (v.length - 1)
            var y = height - padBot - (v[i] - mn) / (mx - mn) * (height - padTop - padBot)
            pts.push({ x: x, y: y })
        }

        // Subtle horizontal bounds labels when requested
        if (showBounds) {
            ctx.fillStyle = Theme.muted
            ctx.font = "10px 'IBM Plex Mono', monospace"
            ctx.textAlign = "left"
            ctx.textBaseline = "top"
            ctx.fillText(Math.round(rawMax) + unit, 0, 2)
            ctx.textBaseline = "bottom"
            ctx.fillText(Math.round(rawMin) + unit, 0, height - 2)
        }

        // Soft vertical gradient fill under the curve
        var grad = ctx.createLinearGradient(0, padTop, 0, height)
        grad.addColorStop(0, Qt.rgba(lineColor.r, lineColor.g, lineColor.b, 0.28))
        grad.addColorStop(1, Qt.rgba(lineColor.r, lineColor.g, lineColor.b, 0.0))
        ctx.beginPath()
        ctx.moveTo(pts[0].x, height)
        for (var j = 0; j < pts.length; j++)
            ctx.lineTo(pts[j].x, pts[j].y)
        ctx.lineTo(pts[pts.length - 1].x, height)
        ctx.closePath()
        ctx.fillStyle = grad
        ctx.fill()

        // Main line
        ctx.strokeStyle = lineColor
        ctx.lineWidth = 2
        ctx.lineJoin = "round"
        ctx.lineCap = "round"
        ctx.beginPath()
        for (var k = 0; k < pts.length; k++) {
            if (k === 0) ctx.moveTo(pts[k].x, pts[k].y)
            else ctx.lineTo(pts[k].x, pts[k].y)
        }
        ctx.stroke()

        // Current value dot at the right end
        var last = pts[pts.length - 1]
        ctx.fillStyle = lineColor
        ctx.beginPath()
        ctx.arc(last.x, last.y, 3, 0, Math.PI * 2)
        ctx.fill()
    }
}
