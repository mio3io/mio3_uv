translation_dict = {
    "zh_HANS": {
        # 选项
        ("*", "UV Sync Auto Select"): "选择同步自动选择",
        ("*", "Use Legacy UI Layout"): "传统UI布局",

        # 常用
        ("Operator", "Horizontal"): "水平",
        ("Operator", "Vertical"): "垂直",
        ("*", "UV Space"): "UV 空间",
        ("*", "Arrange"): "调整",
        ("*", "Composite Edges"): "复合边缘",
        ("*", "Padding"): "填充",
        ("*", "Base Axis"): "基准轴",
        ("*", "Align H"): "水平对齐",
        ("*", "Align V"): "垂直对齐",
        ("*", "Top Align"): "顶部对齐",
        ("*", "Middle Align"): "居中对齐",
        ("*", "Bottom Align"): "底部对齐",
        ("*", "Left Align"): "左对齐",
        ("*", "Right Align"): "右对齐",
        ("*", "Wrap Count"): "换行次数",
        ("*", "Reverse Order"): "反转顺序",
        ("*", "Keep Aspect Ratio"): "保持纵横比",
        ("*", "Keep Position"): "保持位置",
        ("*", "Keep Angle"): "保持角度",
        ("*", "Keep Scale"): "保持比例",
        ("*", "Keep Pin"): "保持钉住",
        ("*", "Keep Seam"): "保持缝线",
        ("*", "Keep Boundary"): "保持边界",

        # 展开
        ("Operator", "UV Unwrap"): "UV 展开",
        ("*", "Position and Scale"): "位置和缩放",
        ("*", "Keep Position, Scale, Angle"): "保持位置、缩放和角度",
        ("*", "Unwrap Horizontal(X) Only"): "仅水平(X 轴)展开",
        ("*", "Unwrap Vertical(Y) Only"): "仅垂直(Y轴)展开",
        ("Operator", "Straight"): "直线",
        ("*", "Unwrap selected edge loop to a straight line"): "将选中的边缘环展开为直线",
        ("Operator", "Rectify"): "矩形化",
        ("*", "Unwrap boundary to rectangle using four corners or a range as reference"): "使用四个角或范围作为参考将边界展开为矩形",
        ("Operator", "Gridify"): "网格化",
        ("*", "Align UVs of a quadrangle in a grid"): "将四边形的UV在网格中对齐",
        ("*", "Projection Unwrap"): "投影展开",
        ("*", "Unwrap linked faces"): "展开连接的面",
        ("*", "Unwrap by linked mesh"): "按链接的网格展开",

        ("Operator", "Mark Seam by Angle"): "按角度标记缝线",
        ("Operator", "Mark Seam by Boundary"): "按边界标记缝线",
        ("*", "Exclude Angle"): "排除角度",
        ("*", "Box Wrap Point"): "盒子包裹点",
        ("*", "Front Angle Threshold"): "正面角度阈值",
        ("*", "Clear Seam"): "清除缝线",
        ("*", "Clear Original Seam"): "清除原始缝线",

        # 对齐
        ("*", "Fixed Mode"): "固定模式",
        ("*", "Island Mode"): "岛屿模式",
        ("*", "Edge Mode"): "边缘模式",
        ("*", "Process each edge loops"): "处理每个边缘环",
        ("*", "Process multiple edge loops as a single group"): "将多个边缘环作为一个组处理",

        ("Operator", "Sort"): "排序",
        ("Operator", "Align UVs"): "对齐 UV",
        ("*", "Align UVs"): "对齐 UV",
        ("*", "Align UVs of vertices, edge loops and islands"): "对齐顶点、边缘环和岛屿的 UV",
        ("*", "Align Edge Loops"): "对齐边缘环",
        ("Operator", "Orient Edge"): "边缘对齐",
        ("*", "Align the selected edge or island to an axis"): "根据选定的边缘或岛屿对齐轴",
        ("Operator", "Align Axis"): "轴对齐",
        ("Operator", "Orient World"): "世界方向对齐",
        ("Operator", "Align Seam"): "缝线对齐",
        ("*", "Align UVs of the same 3D vertex split by a seam"): "对齐被缝线分割的相同3D顶点的UV",
        ("*", "Align the width of islands or UV groups"): "对齐岛屿或UV组的宽度",
        ("Operator", "Distribute"): "分布",
        ("*", "Distribute islands evenly"): "均匀分布岛屿",
        ("*", "Distribute"): "分布",
        ("Operator", "Stretch Island"): "拉伸岛屿",
        ("Operator", "Stretch"): "拉伸",

        # 顶点
        ("Operator", "Distribute UVs"): "分布 UV",
        ("*", "Island Mode: Distribute islands evenly spaced\nUV Group: evenly spaced or based on geometry"): "均匀分布UV或基于几何形状分布",
        ("Operator", "Circular"): "圆形",
        ("*", "Shape the edge loop into a circular shape"): "将边缘环塑造成圆形",
        ("Operator", "Offset"): "偏移",
        ("*", "Expand/Shrink UV Borders"): "扩展/缩小 UV 边界",

        # 岛屿
        ("Operator", "Sort Islands"): "排序岛屿",
        ("*", "Rearrange islands based on coordinates in 3D space"): "根据3D空间中的坐标重新排序岛屿",
        ("*", "Sort Method"): "排序方法",
        ("*", "Start Angle (Clock)"): "起始角度(时钟方向)",
        ("Operator", "Island Margin"): "岛屿间距",

        ("Operator", "Stack"): "堆叠",
        ("*", "Overlap similar UV shapes"): "重叠相似的UV形状",
        ("Operator", "Shuffle"): "随机排列",
        ("Operator", "Unify UV Shapes"): "统一UV形状",
        ("Operator", "Average Island Scales"): "平均岛屿大小",
        ("Operator", "Average Scales"): "平均大小",

        # 组
        ("Operator", "Grid Sort"): "网格排序",
        ("*", "Gridding island based on coordinates in 3D space"): "根据3D空间中的坐标对岛屿进行网格排序",
        ("*", "Grid Threshold"): "网格阈值",
        ("*", "UV Distance"): "UV距离",
        ("*", "UV Similar"): "UV相似度",
        ("*", "Grid Size"): "网格大小",
        ("*", "Align Type"): "对齐类型",
        ("*", "Align by group"): "按组对齐",
        ("*", "Group Margin"): "组间距",

        ("Operator", "Unfoldify"): "展开图",
        ("*", "Arrange islands vertically and horizontally based on their positional relationships in 3D space"): "根据岛屿在 3D 空间中的位置关系，垂直和水平排列岛屿",
        ("*", "Group Rearrange"): "组重新排列",
        ("*", "Group by Linked Faces"): "按连接的面分组",
        ("*", "Based on Active"): "基于活动对象",
        ("*", "Orient World"): "世界方向对齐",

        ("Operator", "Auto Body Parts"): "自动对齐身体部位",
        ("*", "Select hair strands or fingers to auto-align rotation and order.\nClassify by parts if whole body is selected"): "选择头发束或手指以自动对齐旋转和顺序。\n如果选择整个身体，则按部位分类",
        ("Operator", "Hand L"): "左手",
        ("Operator", "Hand R"): "右手",
        ("Operator", "Foot L"): "左脚",
        ("Operator", "Foot R"): "右脚",
        ("Operator", "Button"): "按钮",
        ("Operator", "Front Hair"): "前发",
        ("Operator", "Back Hair"): "后发",

        # 对称
        ("*", "Symmetrize based on 3D space"): "基于3D空间对称化UV",
        ("Operator", "Snap"): "对齐",
        ("*", "Symmetrize based on UV space"): "基于UV空间对称化",

        # 选择
        ("Operator", "Select Half"): "选择一半",
        ("*", "Select UVs on one side of the axis in 3D space"): "选择3D空间中轴的一侧的UV",
        ("Operator", "Shared Vert"): "共享顶点",
        ("Operator", "Similar"): "相似",
        ("*", "Odd UVs"): "特殊 UV",
        ("Operator", "No Region"): "无区域",
        ("Operator", "Flipped"): "翻转",
        ("*", "Select Flipped UV Faces"): "选择翻转的UV面",
        ("*", "Select Zero Area UV Faces"): "选择面积为零的UV面",
        ("Operator", "Boundary"): "边界",
        ("*", "Select Boundary"): "选择边界",
        ("*", "UV Space Boundary"): "UV 空间边界",
        ("Operator", "Select Edge Loops"): "选择边缘环",
        ("*", "Select only vertical or horizontal edges"): "仅选择垂直或水平边缘",

        # 工具
        ("Operator", "Checker Map"): "棋盘格贴图",
        ("Operator", "Clear Checker Map"): "清除棋盘格贴图",
        ("*", "Set the checker map (using Geometry Nodes)"): "设置棋盘格贴图(使用几何节点)",
        ("Operator", "Preview Padding"): "预览填充",
        ("*", "Preview the padding lines"): "预览填充线",
        ("*", "Warning: This option may poor performance"): "警告：此选项可能会降低性能",
        ("Operator", "UV Mesh"): "UV 网格",
        ("*", "Auto Scaling"): "自动缩放",
        ("*", "Set up a modifier for UV to Mesh (using Geometry Nodes)"): "设置UV到网格的修改器(使用几何节点)",

        ("*", "Please display an image if you want to use pixel units"): "如需使用像素单位，请显示图像",
    }
}  # fmt: skip
