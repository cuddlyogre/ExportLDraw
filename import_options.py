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

    defaults['chosen_logo'] = "logo3"
    chosen_logo = defaults['chosen_logo']

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

    defaults['smooth_type'] = ["edge_split", "auto_smooth", "bmesh_split"][0]
    smooth_type = defaults['smooth_type']

    defaults['gap_target'] = ["object", "mesh"][0]
    gap_target = defaults['gap_target']

    defaults['gap_scale_strategy'] = ["constraint", "object"][1]
    gap_scale_strategy = defaults['gap_scale_strategy']

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

    defaults['treat_models_with_subparts_as_parts'] = True
    treat_models_with_subparts_as_parts = defaults['treat_models_with_subparts_as_parts']
