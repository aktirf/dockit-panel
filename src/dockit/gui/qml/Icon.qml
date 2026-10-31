import QtQuick
import QtQuick.Shapes

Item {
    id: root
    property string name: ""
    property color color: "white"
    property real size: 20
    property real stroke: 2
    width: size
    height: size
    implicitWidth: size
    implicitHeight: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        antialiasing: true
        layer.enabled: true
        layer.samples: 4

        ShapePath {
            strokeColor: root.color
            strokeWidth: root.stroke
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: Icons.paths[root.name] || "" }
        }
    }
}
