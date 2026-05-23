from datetime import datetime


def parse_date(d):
  if d is None:
    return None

  for fmt in (
    "%B %d, %Y",
    "%B %Y",
    "%d-%b-%Y",
    "%Y-%m", 
    "%Y", 
    "%m/%d/%Y",
    ):

    try:
      return datetime.strptime(d, fmt)
    except ValueError:
      continue
    
  return None


def check_compliance_date(refDt, docDt):
  if not refDt:
    return "Needs Manual Review"
  elif not docDt or not str(docDt).strip() or docDt in ("Current", "**", "N/A", "TBD"):
    return "Needs Manual Review"
  
  refP = parse_date(refDt)
  docP = parse_date(docDt)
  
  if docP is None or refP is None:
    return "Needs Manual Review"
  elif docP == refP:
    return "Current"
  elif docP < refP:
    return "Not Current"
  else:
    return "Current"