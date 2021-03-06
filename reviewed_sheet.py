import os
from datetime import datetime, timedelta

import requests
from beem.account import Account
from beem.comment import Comment
from beem.exceptions import ContentDoesNotExistsException

import constants
from contribution import Contribution


def exponential_vote(score, category, url, vipo=False):
    """Calculates the exponential vote for the bot."""
    status = ""

    try:
        max_vote = constants.MAX_VOTE[category]
    except:
        max_vote = constants.MAX_TASK_REQUEST

    if vipo:
        max_vote *= 1.2

    if score < constants.MINIMUM_SCORE:
        weight = 0.0
    else:
        status = "Pending"
        power = constants.EXP_POWER
        weight = pow(
            score / 100.0,
            power - (score / 100.0 * (power - 1.0))) * max_vote

    return status, f"{weight:.2f}"


def vote_contribution(contribution):
    """Votes on the contribution with a scaled weight (dependent on the
    contribution's category and weight).
    """
    if "@amosbastian" in contribution.url:
        return

    weight = (float(contribution.weight) /
              max(constants.MAX_VOTE.values()) * 100.0) / constants.SCALER
    contribution = Comment(contribution.url)
    voters = [vote.voter for vote in contribution.get_votes()]
    if "amosbastian" not in voters:
        contribution.vote(weight, "amosbastian")


def add_comment(contribution):
    """Adds the authorperm of the moderator's comment to the database."""
    if contribution.moderator == "amosbastian":
        return

    post = Comment(contribution.url)

    inserted = False
    for comment in post.get_replies():
        if comment.author == contribution.moderator:
            age = comment.time_elapsed()
            collection = constants.DB.comments
            collection.insert({
                "url": comment.authorperm,
                "upvote_time": datetime.now() + timedelta(minutes=10) - age,
                "inserted": datetime.now(),
                "upvoted": False,
                "category": contribution.category
            })
            inserted = True

    if not inserted:
        collection = constants.DB.missed_posts
        collection.insert({
            "url": contribution.url,
            "moderator": contribution.moderator,
            "category": contribution.category
        })


def move_to_reviewed(contribution, post):
    """Move contribution to the reviewed worksheet."""
    constants.REVIEWED.append_row(list(contribution.__dict__.values()))


def main():
    result = constants.UNREVIEWED.get_all_values()
    vipo = constants.VIPO
    is_vipo = False

    already_voted_on = [contribution["url"] for contribution in
                        constants.DB_UTEMPIAN.contributions.find({
                            "status": "unreviewed",
                            "voted_on": True
                        })]

    for row in result[1:]:
        contribution = Contribution(row)
        moderator = contribution.moderator
        score = contribution.score

        if ((moderator != "" and score != "") or
                contribution.url in already_voted_on):
            today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            contribution.review_date = today

            try:
                post = Comment(contribution.url)
            except ContentDoesNotExistsException:
                constants.UNREVIEWED.delete_row(result.index(row) + 1)
                return

            if contribution.url in already_voted_on:
                contribution.moderator = "IGNORE"
                contribution.score = 0
                contribution.weight = 0
                constants.UNREVIEWED.delete_row(result.index(row) + 1)
                move_to_reviewed(contribution, post)
                continue

            if post.author in vipo:
                is_vipo = True

            category = contribution.category.strip()
            contribution.vote_status, contribution.weight = exponential_vote(
                float(score), category, contribution.url, is_vipo)

            if not moderator.upper() in ["BANNED", "IGNORED", "IGNORE",
                                         "IRRELEVANT"]:
                contribution.review_status = "Pending"

            constants.LOGGER.info(
                f"Moving {contribution.url} to reviewed sheet with voting % "
                f"{contribution.weight} and score {score}")

            constants.UNREVIEWED.delete_row(result.index(row) + 1)
            move_to_reviewed(contribution, post)

            if float(score) > constants.MINIMUM_SCORE:
                vote_contribution(contribution)
                add_comment(contribution)
            return

if __name__ == '__main__':
    main()
