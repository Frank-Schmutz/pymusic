from questionary import ValidationError

def validate_pos_int(i: str):
    return validate_number(i, False, True)

def validate_neg_int(i: str):
    return validate_number(i, False, False)

def validate_pos_float(i: str):
    return validate_number(i, True, True)

def validate_neg_float(i: str):
    return validate_number(i, True, False)

def validate_number(i: str, is_float: bool, pos: bool):
    if not i:
        return True
    try:
        parsed = float(i) if is_float else int(i)
        if (pos and int(parsed) < 0) or (not pos and int(parsed) > 0):
            raise ValueError
    except:
        raise ValidationError(message=f"Must be a {'positive' if pos else 'negative'} {'float' if is_float else 'integer'}")
    return True