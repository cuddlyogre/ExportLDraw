# TODO: remove class
class ImportOptions:
    defaults = {}

    defaults['remove_doubles'] = True
    remove_doubles = defaults['remove_doubles']

    defaults['recalculate_normals'] = False
    recalculate_normals = defaults['recalculate_normals']

    defaults['merge_distance'] = 0.05
    merge_distance = defaults['merge_distance']

    defaults['triangulate'] = False
    triangulate = defaults['triangulate']

    defaults['meta_bfc'] = True
    meta_bfc = defaults['meta_bfc']

    defaults['meta_group'] = True
    meta_group = defaults['meta_group']

    defaults['meta_print_write'] = False
    meta_print_write = defaults['meta_print_write']

    defaults['meta_step'] = False
    meta_step = defaults['meta_step']

    defaults['meta_step_groups'] = False
    meta_step_groups = defaults['meta_step_groups']

    defaults['meta_clear'] = False
    meta_clear = defaults['meta_clear']

    defaults['meta_pause'] = False
    meta_pause = defaults['meta_pause']

    defaults['meta_save'] = False
    meta_save = defaults['meta_save']

    defaults['meta_texmap'] = True
    meta_texmap = defaults['meta_texmap']

    defaults['display_logo'] = False
    display_logo = defaults['display_logo']

    # cast items as list or "EnumProperty(..., default='logo3'): not found in enum members" and a messed up menu
    chosen_logo_choices = list(((logo, logo, logo) for logo in ["logo", "logo2", "logo3", "logo4", "logo5", "high-contrast"]))

    defaults['chosen_logo'] = 2
    chosen_logo = defaults['chosen_logo']

    @staticmethod
    def chosen_logo_value():
        return ImportOptions.chosen_logo_choices[ImportOptions.chosen_logo][0]

    defaults['shade_smooth'] = True
    shade_smooth = defaults['shade_smooth']

    defaults['make_gaps'] = True
    make_gaps = defaults['make_gaps']

    defaults['gap_scale'] = 0.997
    gap_scale = defaults['gap_scale']

    defaults['no_studs'] = False
    no_studs = defaults['no_studs']

    defaults['set_end_frame'] = True
    set_end_frame = defaults['set_end_frame']

    defaults['starting_step_frame'] = 1
    starting_step_frame = defaults['starting_step_frame']

    defaults['frames_per_step'] = 3
    frames_per_step = defaults['frames_per_step']

    defaults['set_timeline_markers'] = False
    set_timeline_markers = defaults['set_timeline_markers']

    smooth_type_choices = (
        ("edge_split", "Edge split", "Use an edge split modifier"),
        ("auto_smooth", "Auto smooth", "Use auto smooth"),
        ("bmesh_split", "bmesh smooth", "Split during initial mesh processing"),
    )

    defaults['smooth_type'] = 2
    smooth_type = defaults['smooth_type']

    @staticmethod
    def smooth_type_value():
        return ImportOptions.smooth_type_choices[ImportOptions.smooth_type][0]

    defaults['import_edges'] = False
    import_edges = defaults['import_edges']

    defaults['bevel_edges'] = False
    bevel_edges = defaults['bevel_edges']

    defaults['bevel_weight'] = 0.3
    bevel_weight = defaults['bevel_weight']

    defaults['bevel_width'] = 0.3
    bevel_width = defaults['bevel_width']

    defaults['bevel_segments'] = 4
    bevel_segments = defaults['bevel_segments']

    defaults['use_freestyle_edges'] = False
    use_freestyle_edges = defaults['use_freestyle_edges']

    defaults['import_scale'] = 0.02
    import_scale = defaults['import_scale']

    defaults['parent_to_empty'] = True  # True False
    parent_to_empty = defaults['parent_to_empty']

    defaults['treat_shortcut_as_model'] = False  # TODO: if true parent to empty at median of group
    treat_shortcut_as_model = defaults['treat_shortcut_as_model']

    color_strategy_choices = (
        ("material", "Material", "Object color is set through the material. Easier to work with but slightly slower to import"),
        ("vertex_colors", "Vertex Colors", "Mesh color is set through vertex colors. More difficult to work with but slightly quicker to import"),
    )

    defaults['color_strategy'] = 0
    color_strategy = defaults['color_strategy']

    @staticmethod
    def color_strategy_value():
        return ImportOptions.color_strategy_choices[ImportOptions.color_strategy][0]
