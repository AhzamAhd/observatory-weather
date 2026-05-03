import pandas as pd
from datetime import datetime
from db import query_df, execute, fetch_one


def add_review(
    observatory,
    reviewer_name,
    rating,
    review_text,
    visit_date,
    telescope_used,
    objects_observed,
    seeing_rating,
    darkness_rating,
    access_rating
):
    """Add a new review to the database."""
    try:
        execute("""
            INSERT INTO observatory_reviews (
                observatory,
                reviewer_name,
                rating,
                review_text,
                visit_date,
                telescope_used,
                objects_observed,
                seeing_rating,
                darkness_rating,
                access_rating,
                created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """, [
            observatory,
            reviewer_name,
            rating,
            review_text,
            visit_date,
            telescope_used,
            objects_observed,
            seeing_rating,
            darkness_rating,
            access_rating,
            datetime.utcnow()
        ])
        return True, "Review submitted successfully!"
    except Exception as e:
        return False, f"Error: {e}"


def get_reviews(observatory=None, limit=50):
    """Get reviews for an observatory or all reviews."""
    if observatory:
        return query_df("""
            SELECT
                reviewer_name,
                rating,
                review_text,
                visit_date,
                telescope_used,
                objects_observed,
                seeing_rating,
                darkness_rating,
                access_rating,
                created_at
            FROM observatory_reviews
            WHERE observatory = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, [observatory, limit])
    else:
        return query_df("""
            SELECT
                observatory,
                reviewer_name,
                rating,
                review_text,
                visit_date,
                telescope_used,
                objects_observed,
                seeing_rating,
                darkness_rating,
                access_rating,
                created_at
            FROM observatory_reviews
            ORDER BY created_at DESC
            LIMIT %s
        """, [limit])


def get_observatory_stats(observatory):
    """
    Get aggregated rating stats for an observatory.
    """
    return fetch_one("""
        SELECT
            COUNT(*)                        AS total_reviews,
            ROUND(AVG(rating)::numeric, 1)  AS avg_rating,
            ROUND(AVG(seeing_rating)::numeric, 1)
                                            AS avg_seeing,
            ROUND(AVG(darkness_rating)::numeric, 1)
                                            AS avg_darkness,
            ROUND(AVG(access_rating)::numeric, 1)
                                            AS avg_access,
            MAX(created_at)                 AS last_review
        FROM observatory_reviews
        WHERE observatory = %s
    """, [observatory])


def get_top_rated_observatories(limit=20):
    """
    Get top rated observatories by average rating.
    Minimum 1 review required.
    """
    return query_df("""
        SELECT
            observatory,
            COUNT(*)                        AS total_reviews,
            ROUND(AVG(rating)::numeric, 1)  AS avg_rating,
            ROUND(AVG(seeing_rating)::numeric, 1)
                                            AS avg_seeing,
            ROUND(AVG(darkness_rating)::numeric, 1)
                                            AS avg_darkness,
            ROUND(AVG(access_rating)::numeric, 1)
                                            AS avg_access,
            MAX(visit_date)                 AS latest_visit
        FROM observatory_reviews
        GROUP BY observatory
        HAVING COUNT(*) >= 1
        ORDER BY avg_rating DESC, total_reviews DESC
        LIMIT %s
    """, [limit])


def get_recent_reviews(limit=10):
    """Get most recent reviews across all observatories."""
    return query_df("""
        SELECT
            observatory,
            reviewer_name,
            rating,
            review_text,
            visit_date,
            telescope_used,
            created_at
        FROM observatory_reviews
        ORDER BY created_at DESC
        LIMIT %s
    """, [limit])


def get_rating_distribution(observatory):
    """Get count of each star rating for an observatory."""
    return query_df("""
        SELECT
            rating,
            COUNT(*) AS count
        FROM observatory_reviews
        WHERE observatory = %s
        GROUP BY rating
        ORDER BY rating DESC
    """, [observatory])


def stars(rating, max_stars=5):
    """Convert numeric rating to star string."""
    if rating is None:
        return "No rating"
    filled = "⭐" * int(round(float(rating)))
    return filled if filled else "No rating"


def rating_color(rating):
    """Get color for a rating value."""
    if rating is None:
        return "#888"
    r = float(rating)
    if r >= 4.5:   return "#1D9E75"
    elif r >= 3.5: return "#378ADD"
    elif r >= 2.5: return "#EF9F27"
    else:          return "#E24B4A"


if __name__ == "__main__":
    print("\n  Reviews system test\n")

    # Add a test review
    success, msg = add_review(
        observatory      = "5  Maunakea",
        reviewer_name    = "Test User",
        rating           = 5,
        review_text      = "Outstanding site. Exceptional seeing conditions above the cloud layer.",
        visit_date       = "2026-04-15",
        telescope_used   = "16-inch Dobsonian",
        objects_observed = "M42, M31, Jupiter",
        seeing_rating    = 5,
        darkness_rating  = 5,
        access_rating    = 3
    )
    print(f"  Add review: {msg}")

    # Get stats
    stats = get_observatory_stats("5  Maunakea")
    if stats:
        print(f"  Total reviews: {stats['total_reviews']}")
        print(f"  Avg rating:    {stats['avg_rating']}")

    # Get top rated
    top = get_top_rated_observatories()
    if not top.empty:
        print(f"\n  Top rated observatories:")
        for _, row in top.iterrows():
            print(
                f"    {row['observatory'][:30]} "
                f"— {row['avg_rating']} "
                f"({row['total_reviews']} reviews)"
            )
    print()