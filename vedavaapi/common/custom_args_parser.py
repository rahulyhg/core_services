from .api_common import jsonify_argument, check_argument_type


def parse_json_args(args, parse_directives):
    args = args.copy()

    for field, field_parse_directives in parse_directives.items():

        value = args.get(field, None)
        jsonified_value = jsonify_argument(value, key=field) or field_parse_directives.get('default', None)
        if 'allowed_types' in field_parse_directives:
            check_argument_type(
                jsonified_value, field_parse_directives['allowed_types'],
                key=field, allow_none=field_parse_directives.get('allow_none', False))

        if 'custom_validator' in field_parse_directives:
            field_parse_directives['custom_validator'](jsonified_value)

        args[field] = jsonified_value

    return args
