"""Generate a realistic sample CSV for testing the Collection Analyzer."""

import csv
import random
from datetime import datetime, timedelta

SUBJECTS_BY_CLASS = {
    "A": ("General Works", ["Reference", "Encyclopedias"]),
    "B": ("Philosophy & Psychology", ["Ethics", "Psychology", "Logic"]),
    "D": ("World History", ["European History", "Asian History", "African History"]),
    "E": ("American History", ["Colonial Period", "Civil War", "20th Century"]),
    "F": ("Local History", ["State History", "Local History"]),
    "G": ("Geography", ["Maps", "Travel", "Anthropology"]),
    "H": ("Social Sciences", ["Economics", "Sociology", "Finance"]),
    "J": ("Political Science", ["Government", "International Relations"]),
    "K": ("Law", ["Constitutional Law", "Criminal Law"]),
    "L": ("Education", ["Teaching Methods", "Higher Education"]),
    "M": ("Music", ["Theory", "Instruments", "Composers"]),
    "N": ("Fine Arts", ["Painting", "Sculpture", "Photography"]),
    "P": ("Language & Literature", ["Fiction", "Poetry", "Drama", "ESL"]),
    "Q": ("Science", ["Mathematics", "Physics", "Biology", "Chemistry"]),
    "R": ("Medicine", ["Public Health", "Nursing", "Nutrition"]),
    "S": ("Agriculture", ["Farming", "Gardening", "Forestry"]),
    "T": ("Technology", ["Engineering", "Computing", "Manufacturing"]),
    "Z": ("Library Science", ["Bibliography", "Information Science"]),
}

FORMATS = ["Book", "Book", "Book", "Book", "DVD", "Audiobook", "Large Print",
           "eBook", "Periodical", "CD"]

AUTHORS = [
    "Smith, John", "Johnson, Mary", "Williams, Robert", "Brown, Patricia",
    "Jones, Michael", "Garcia, Maria", "Miller, David", "Davis, Jennifer",
    "Rodriguez, Carlos", "Martinez, Ana", "Hernandez, Luis", "Lopez, Laura",
    "Wilson, James", "Anderson, Linda", "Thomas, Richard", "Taylor, Barbara",
    "Moore, William", "Jackson, Elizabeth", "Martin, Joseph", "Lee, Susan",
    "Thompson, Charles", "White, Margaret", "Harris, Christopher",
    "Clark, Dorothy", "Lewis, Daniel", "Robinson, Nancy", "Walker, Paul",
    "Young, Karen", "Allen, Mark", "King, Betty", "Wright, Steven",
    "Scott, Sandra", "Green, Andrew", "Baker, Donna", "Adams, Kenneth",
    "Nelson, Helen", "Hill, George", "Ramirez, Lisa", "Campbell, Edward",
    "Mitchell, Ruth", "Roberts, Brian", "Carter, Sharon", "Phillips, Kevin",
    "Evans, Deborah", "Turner, Ronald", "Torres, Cynthia", "Parker, Jeffrey",
    "Collins, Carolyn", "Edwards, Timothy", "Stewart, Janet",
]


def generate_sample(n: int = 500) -> list[dict]:
    """Generate n sample catalog records."""
    random.seed(42)
    records = []
    current_year = datetime.now().year

    # Intentionally create imbalances for gap detection:
    # - Heavy on P (Literature) and H (Social Sciences)
    # - Light on M (Music), K (Law), S (Agriculture)
    # - Aging materials in Q (Science) and T (Technology)
    weight_map = {
        "A": 5, "B": 30, "D": 20, "E": 25, "F": 10, "G": 15,
        "H": 60, "J": 15, "K": 5, "L": 20, "M": 5, "N": 15,
        "P": 120, "Q": 40, "R": 25, "S": 3, "T": 35, "Z": 5,
    }

    classes = []
    for cls, weight in weight_map.items():
        classes.extend([cls] * weight)

    for i in range(n):
        lc_class = random.choice(classes)
        info = SUBJECTS_BY_CLASS[lc_class]

        # Year distribution: bias older for Q and T to create aging gaps
        if lc_class in ("Q", "T"):
            year = random.choice(
                list(range(1985, 2010)) * 3 + list(range(2010, current_year + 1))
            )
        elif lc_class == "P":
            year = random.randint(1990, current_year)
        else:
            year = random.randint(1970, current_year)

        # Circulation: newer items tend to circulate more
        age = current_year - year
        if age < 5:
            checkouts = random.choice([0, 1, 2, 3, 5, 8, 12, 15, 20])
        elif age < 15:
            checkouts = random.choice([0, 0, 1, 2, 3, 5, 8])
        else:
            checkouts = random.choice([0, 0, 0, 0, 1, 1, 2])

        fmt = random.choice(FORMATS)
        call_num = f"{lc_class}{random.randint(1, 999)}.{random.choice('ABCDEFGH')}{random.randint(1, 99)}"
        subject = random.choice(info[1])
        author = random.choice(AUTHORS)

        title_words = [
            "The", "A", "Introduction to", "Understanding", "Exploring",
            "Modern", "Essential", "Complete Guide to", "Handbook of",
            "Principles of", "Foundations of", "Advanced", "New",
        ]
        title_subject = [
            subject, info[0], f"{subject} Today",
            f"{subject} in Practice", f"American {subject}",
            f"World {subject}", f"{subject} Theory",
        ]
        title = f"{random.choice(title_words)} {random.choice(title_subject)}"

        # Date added: usually within a year or two of pub year
        added_year = min(year + random.randint(0, 2), current_year)
        date_added = datetime(added_year, random.randint(1, 12), random.randint(1, 28))

        last_checkout = None
        if checkouts > 0:
            days_ago = random.randint(1, age * 365 + 365)
            last_checkout = datetime.now() - timedelta(days=days_ago)

        price = round(random.uniform(8.99, 45.99), 2)

        records.append({
            "Title": title,
            "Author": author,
            "ISBN": f"978{random.randint(1000000000, 9999999999)}",
            "Call Number": call_num,
            "Publication Year": year,
            "Subject": subject,
            "Material Type": fmt,
            "Location": random.choice(["Main", "Main", "Main", "Children", "YA"]),
            "Barcode": f"3{random.randint(1000000000000, 9999999999999)}",
            "Total Checkouts": checkouts,
            "Last Checkout Date": (
                last_checkout.strftime("%m/%d/%Y") if last_checkout else ""
            ),
            "Created Date": date_added.strftime("%m/%d/%Y"),
            "Item Status": random.choice(
                ["Available", "Available", "Available", "Checked Out", "In Transit"]
            ),
            "Price": price,
            "Collection": random.choice(
                ["Adult Non-Fiction", "Adult Fiction", "Juvenile", "YA", "Reference"]
            ),
        })

    return records


def main():
    records = generate_sample(500)
    filepath = "sample_data/sample_catalog.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"Generated {len(records)} sample records in {filepath}")


if __name__ == "__main__":
    main()
