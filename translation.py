import bpy

translation_dict = {
    "ja_JP": {
        ("*", "Straight"): "ストレート",
        ("*", "Unwrap selected edge loop to a straight line"): "選択したエッジループが直線になるように展開する",
        ("*", "Rectify"): "矩形",
        ("*", "Unwrap boundary to rectangle using four corners or a range as reference"): "基準のコーナー4点または範囲を選択し境界が矩形になるように展開する",
        ("*", "Gridify"): "グリッド",
        ("*", "Align UVs of a quadrangle in a grid"): "四角形のUVをグリッド状に整列させる",
        ("*", "Projection Unwrap"): "投影展開",
        ("*", "Unwrap linked faces"): "リンク面を展開",
        ("*", "Unwrap by linked mesh"): "メッシュごとに投影",

        ("*", "Mark Seam by Angle"): "角度でシームを設定",
        ("*", "Mark Seam by Boundary"): "選択境界にシームを設定",
        ("*", "Exclude Angle"): "正面にシームを入れない",
        ("*", "Box Wrap Point"): "ボックスの折り返し",
        ("*", "Front Angle Threshold"): "正面に含む角度",
        ("*", "Celar Seam"): "シームをクリア",
        ("*", "Clear Original Seam"): "元のシームをクリア",

        ("*", "Align UVs"): "UVを整列",
        ("*", "Align UVs of vertices, edge loops and islands"): "頂点・辺ループ・アイランドのUVを整列させる",
        ("*", "Align Edge Loops"): "辺ループを整列",
        ("*", "Orient Edge"): "辺で整列",
        ("*", "Axis-align the island to the selected edge"): "選択した辺を基準にアイランドを軸整列させる",
        ("*", "Align Axis"): "軸整列",
        ("*", "Orient World"): "ワールド方向",
        ("*", "Align Seam"): "シーム整列",
        ("*", "Align UVs of the same 3D vertex split by a seam"): "シームで別れた同じ3D頂点を持つUV座標を整列します",

        ("*", "Island Mode"): "アイランドモード",
        ("*", "Edge Mode"): "辺モード",
        ("*", "Process each edge loops"): "エッジループ毎に処理する",
        ("*", "Fixed Mode"): "モード固定",

        ("*", "Relax"): "Relax",
        ("*", "Offset Boundary"): "オフセット",

        ("*", "UV Space"): "UV空間",
        ("*", "Base Axis"): "基準軸",
        ("*", "Arrange"): "調整",

        ("*", "Keep Position"): "位置を維持",
        ("*", "Keep Angle"): "角度を維持",
        ("*", "Keep Scale"): "スケールを維持",
        ("*", "Keep Pin"): "ピンを維持",
        ("*", "Keep Seam"): "シームを維持",

        ("*", "Keep Aspect"): "アスペクトを維持",

        ("*", "Unify Shapes"): "UVの形状を揃える",
        ("*", "Stack"): "重ねる",
        ("*", "Overlap similar UV shapes"): "類似した形状のUVシェイプを重ねます",
        ("*", "Align the shape based on the first island"): "類似した形状のUVシェイプを重ねます",

        ("*", "Shuffle"): "シャッフル",
        ("*", "Average Island Scales"): "3Dに基づく大きさ",

        ("*", "Fixed Pins"): "ピンを固定",
        ("*", "Fixed Boundary"): "境界を固定",

        ("*", "Sort Method"): "ソート方式",
        ("*", "One Axis"): "単一軸",
        ("*", "Top Align"): "上揃え",
        ("*", "Middle Align"): "中央",
        ("*", "Bottom Align"): "下揃え",
        ("*", "Reorder islands based on coordinates in 3D space"): "3D空間の座標を基準にアイランドを並び替え",
        ("*", "Gridding island based on coordinates in 3D space"): "3D空間の座標を基準にアイランドをグリッド状に並び替え",
        ("*", "Align V"): "横に並べる",
        ("*", "Align H"): "縦に並べる",
        ("*", "Orient"): "向き",
        ("*", "Start Angle (Clock)"): "開始角度（時計）",

        ("*", "Grid Sort"): "グリッド状にソート",
        ("*", "Grid Threshold"): "グリッドのしきい値",
        ("*", "UV Distance"): "UV空間での距離",
        ("*", "UV Similar"): "UVの類似性",
        ("*", "Grid Size"): "グリッド幅",
        ("*", "Align Type"): "整列タイプ",
        ("*", "Align by group"): "グループごとに整列",
        ("*", "Group Margin"): "グループの間隔",
        ("*", "Wrap Count"): "折り返し",
        ("*", "Reverse Order"): "順番を反転",

        ("*", "Rearrange"): "アイランドを並べる",
        ("*", "Group Rearrange"): "グループ化して再配置",
        ("*", "Body Preset"): "パーツにあわせて整列",
        ("*", "Unfoldify"): "展開図レイアウト",

        ("*", "Select hair strands or fingers to auto-align rotation and order.\nClassify by parts if whole body is selected"): "髪の房や指をまとめて選択して自動的に回転と順序を揃えます.\n全身を選択している場合はパーツで分類します",
        ("*", "Hand L"): "左手L",
        ("*", "Hand R"): "右手R",
        ("*", "Foot L"): "左足L",
        ("*", "Foot R"): "右足R",
        ("*", "Button"): "ボタン",
        ("*", "Front Hair"): "前髪",
        ("*", "Back Hair"): "後髪",
        ("*", "Auto Body Parts"): "自動で分類 or 整列",

        ("*", "Symmetrize ←"): "対称化",
        ("*", "Snap"): "スナップ",
        ("*", "Symmetrize based on 3D space"): "3D空間の対称性に基づいてUVを対称化します",
        ("*", "Symmetrize based on UV space"): "UV空間での対称位置にスナップします",

        ("*", "Select Half"): "半分",
        ("*", "Shared"): "同じ頂点",
        ("*", "Similar"): "類似",
        ("*", "Odd UVs"): "特殊UV",
        ("*", "No region"): "領域なし",
        ("*", "Flipped Faces"): "反転した面",
        ("*", "Select Flipped UV Faces"): "反転したUV面を選択します",
        ("*", "Select Zero Area UV Faces"): "領域がゼロのUVを選択",
        ("*", "Select Boundary"): "境界を選択",
        ("*", "UV Space Boundary"): "UV上の境界",
        ("*", "Select UVs on one side of the axis in 3D space"): "3D空間で片方の面を選択",
        ("*", "Select only vertical or horizontal edges"): "垂直または水平のエッジのみを選択",

        ("*", "Checker Map"): "チェッカーマップ",
        ("*", "Preview Padding"): "パディング表示",
        ("*", "Preview the padding lines"): "パディングのラインをプレビューします",
        ("*", "Padding"): "パディング",

    }
}  # fmt: skip


def register(name):
    bpy.app.translations.unregister(name)
    bpy.app.translations.register(name, translation_dict)


def unregister(name):
    bpy.app.translations.unregister(name)
