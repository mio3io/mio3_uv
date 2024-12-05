import bpy

translation_dict = {
    "ja_JP": {
        # Common
        ("Operator", "Horizontal"): "水平",
        ("Operator", "Vertical"): "垂直",
        ("*", "UV Space"): "UV空間",
        ("*", "Arrange"): "調整",
        ("*", "Composite Edges"): "複合エッジ",
        ("*", "Padding"): "パディング",
        ("*", "Base Axis"): "基準軸",
        ("*", "Align H"): "横に並べる",
        ("*", "Align V"): "縦に並べる",
        ("*", "Top Align"): "上揃え",
        ("*", "Middle Align"): "中央",
        ("*", "Bottom Align"): "下揃え",
        ("*", "Wrap Count"): "折り返し",
        ("*", "Reverse Order"): "順番を反転",
        ("*", "Keep Aspect Ratio"): "アスペクト比を維持",
        ("*", "Keep Position"): "位置を維持",
        ("*", "Keep Angle"): "角度を維持",
        ("*", "Keep Scale"): "スケールを維持",
        ("*", "Keep Pin"): "ピンを維持",
        ("*", "Keep Seam"): "シームを維持",
        ("*", "Keep Boundary"): "境界を維持",

        # Unwrap
        ("Operator", "UV Unwrap"): "UV展開",
        ("*", "Position and Scale"): "位置とサイズ",
        ("*", "Keep Position, Scale, Angle"): "位置・サイズ・角度の維持",
        ("Operator", "Unwrap Horizontal(X) Only"): "水平(X軸)のみを展開",
        ("Operator", "Unwrap Vertical(Y) Only"): "垂直(Y軸)のみを展開",
        ("Operator", "Straight"): "ストレート",
        ("*", "Unwrap selected edge loop to a straight line"): "選択したエッジループが直線になるように展開する",
        ("Operator", "Rectify"): "矩形",
        ("*", "Unwrap boundary to rectangle using four corners or a range as reference"): "基準のコーナー4点または範囲を選択し境界が矩形になるように展開する",
        ("Operator", "Gridify"): "グリッド",
        ("*", "Align UVs of a quadrangle in a grid"): "四角形のUVをグリッド状に整列させる",
        ("*", "Projection Unwrap"): "投影展開",
        ("*", "Unwrap linked faces"): "リンク面を展開",
        ("*", "Unwrap by linked mesh"): "メッシュごとに投影",

        ("Operator", "Mark Seam by Angle"): "角度でシームを設定",
        ("Operator", "Mark Seam by Boundary"): "選択境界にシームを設定",
        ("*", "Exclude Angle"): "正面にシームを入れない",
        ("*", "Box Wrap Point"): "ボックスの折り返し",
        ("*", "Front Angle Threshold"): "正面に含む角度",
        ("*", "Celar Seam"): "シームをクリア",
        ("*", "Clear Original Seam"): "元のシームをクリア",

        # Align
        ("*", "Fixed Mode"): "モード固定",
        ("*", "Island Mode"): "アイランドモード",
        ("*", "Edge Mode"): "辺モード",
        ("*", "Process each edge loops"): "エッジループ毎に処理する",
        ("*", "Process multiple edge loops as a single group"): "複数のエッジループをひとつのグループとして処理する",

        ("Operator", "Align UVs"): "UVを整列",
        ("*", "Align UVs"): "UVを整列",
        ("*", "Align UVs of vertices, edge loops and islands"): "頂点・辺ループ・アイランドのUVを整列させる",
        ("*", "Align Edge Loops"): "辺ループを整列",
        ("Operator", "Orient Edge"): "辺で整列",
        ("*", "Axis-align the island to the selected edge"): "選択した辺を基準にアイランドを軸整列させる",
        ("Operator", "Align Axis"): "軸整列",
        ("Operator", "Orient World"): "ワールド方向",
        ("Operator", "Align Seam"): "シーム整列",
        ("*", "Align UVs of the same 3D vertex split by a seam"): "シームで別れた同じ3D頂点を持つUV座標を整列します",
        ("*", "Align the width of islands or UV groups"): "アイランドやUVグループの幅を揃える",
        ("Operator", "Distribute"): "分布",
        ("*", "Distribute islands evenly"): "アイランドを等間隔に分布する",
        ("*", "Distribute"): "分布",
        ("Operator", "Stretch Island"): "ストレッチ",

        # Vertex
        ("Operator", "Relax"): "リラックス",
        ("Operator", "Distribute UVs"): "UVを分布",
        ("*", "Distribute UVs evenly or based on geometry"): "UVを等間隔またはジオメトリに基づくように分布する",
        ("Operator", "Circular"): "円形",
        ("*", "Shape the edge loop into a circular shape"): "エッジループを円形に整える",
        ("Operator", "Offset"): "オフセット",
        ("*", "Expand/Shrink UV Borders"): "境界のUVを拡大/縮小する",

        # Island
        ("Operator", "Sort"): "アイランドをソート",
        ("*", "Reorder islands based on coordinates in 3D space"): "3D空間の座標を基準にアイランドを並び替え",
        ("*", "Sort Method"): "ソート方式",
        ("*", "Start Angle (Clock)"): "開始角度（時計）",
        ("Operator", "Island Margin"): "アイランドの間隔",

        ("Operator", "Stack"): "重ねる",
        ("*", "Overlap similar UV shapes"): "類似した形状のUVシェイプを重ねます",
        ("Operator", "Shuffle"): "シャッフル",
        ("Operator", "Unify Shapes"): "UVの形状を揃える",
        ("Operator", "Average Island Scales"): "3Dに基づく大きさ",

        # Group
        ("Operator", "Grid Sort"): "グリッド",
        ("*", "Gridding island based on coordinates in 3D space"): "3D空間の座標を基準にアイランドをグリッド状に並び替え",
        ("*", "Grid Threshold"): "グリッドのしきい値",
        ("*", "UV Distance"): "UV空間での距離",
        ("*", "UV Similar"): "UVの類似性",
        ("*", "Grid Size"): "グリッド幅",
        ("*", "Align Type"): "整列タイプ",
        ("*", "Align by group"): "グループごとに整列",
        ("*", "Group Margin"): "グループの間隔",

        ("Operator", "Unfoldify"): "展開図",
        ("*", "Group Rearrange"): "グループ化して再配置",
        ("*", "Group by Linked Faces"): "接続した面でグループ化",
        ("*", "Based on Active"): "アクティブをベースに",
        ("*", "Orient World"): "ワールド方向",

        ("Operator", "Auto Body Parts"): "パーツを自動で整列",
        ("*", "Select hair strands or fingers to auto-align rotation and order.\nClassify by parts if whole body is selected"): "髪の房や指をまとめて選択して自動的に回転と順序を揃えます.\n全身を選択している場合はパーツで分類します",
        ("Operator", "Hand L"): "左手L",
        ("Operator", "Hand R"): "右手R",
        ("Operator", "Foot L"): "左足L",
        ("Operator", "Foot R"): "右足R",
        ("Operator", "Button"): "ボタン",
        ("Operator", "Front Hair"): "前髪",
        ("Operator", "Back Hair"): "後髪",

        # Symmetrize
        ("Operator", "Symmetrize"): "対称化",
        ("*", "Symmetrize based on 3D space"): "3D空間の対称性に基づいてUVを対称化します",
        ("Operator", "Snap"): "スナップ",
        ("*", "Symmetrize based on UV space"): "UV空間での対称位置にスナップします",

        # Select
        ("Operator", "Select Half"): "半分",
        ("Operator", "Shared"): "同じ頂点",
        ("Operator", "Similar"): "類似",
        ("*", "Odd UVs"): "特殊UV",
        ("Operator", "No Region"): "領域なし",
        ("Operator", "Flipped"): "反転した面",
        ("*", "Select Flipped UV Faces"): "反転したUV面を選択します",
        ("*", "Select Zero Area UV Faces"): "領域がゼロのUVを選択",
        ("Operator", "Boundary"): "境界",
        ("*", "Select Boundary"): "境界を選択",
        ("*", "UV Space Boundary"): "UV上の境界",
        ("*", "Select UVs on one side of the axis in 3D space"): "3D空間で片方の面を選択",
        ("*", "Select only vertical or horizontal edges"): "垂直または水平のエッジのみを選択",

        # Utils
        ("Operator", "Checker Map"): "チェッカーマップ",
        ("Operator", "Clear Checker Map"): "チェッカーマップをクリア",
        ("*", "Set the checker map (using Geometry Nodes)"): "チェッカーマップを設定します（ジオメトリノードを使用）",
        ("Operator", "Preview Padding"): "パディング表示",
        ("*", "Preview the padding lines"): "パディングのラインをプレビューします",
        ("*", "Warning: This option may poor performance"): "警告: このオプションはパフォーマンスが低下する可能性があります",
        ("Operator", "UV Mesh"): "UV Mesh",
        ("*", "Set up a modifier for UV to Mesh (using Geometry Nodes)"): "UV to Mesh 用のモディファイアを設定します（ジオメトリノードを使用）",

    }
}  # fmt: skip


def register(name):
    bpy.app.translations.unregister(name)
    bpy.app.translations.register(name, translation_dict)


def unregister(name):
    bpy.app.translations.unregister(name)
