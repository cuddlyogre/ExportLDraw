class ExportOptions:
    defaults = {}

    defaults["remove_doubles"] = False
    remove_doubles = defaults["remove_doubles"]

    defaults["merge_distance"] = 0.05
    merge_distance = defaults["merge_distance"]

    defaults["recalculate_normals"] = False
    recalculate_normals = defaults["recalculate_normals"]

    defaults["triangulate"] = False
    triangulate = defaults["triangulate"]

    defaults["ngon_handling"] = "triangulate"
    ngon_handling = defaults["ngon_handling"]

    defaults["selection_only"] = True
    selection_only = defaults["selection_only"]

    defaults["export_precision"] = 2
    export_precision = defaults["export_precision"]
