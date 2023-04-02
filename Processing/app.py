import connexion
from connexion import NoContent
import datetime
import json
import logging
import logging.config
import requests
import yaml
import apscheduler
from apscheduler.schedulers.background import BackgroundScheduler

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
from stats import Stats

DB_ENGINE = create_engine("sqlite:///stats.sqlite")
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def get_latest_stats():
    # TODO create a session
    session = DB_SESSION()

    # TODO query the session for the first Stats record, ordered by Stats.last_updated
    query = session.query(Stats).order_by(Stats.last_updated.desc()).first()

    # TODO  convert it to a dict and return it (with status code 200)
    query = query.to_dict()
    session.close()
    return query, 200


def populate_stats():
    #   IMPORTANT: all stats calculated by populate_stats must be CUMULATIVE
    #
    #   The number of buy and sell events received must be added to the previous total held in stats.sqlite,
    #   and the max_buy_price and max_sell_price must be compared to the values held in stats.sqlite

    #   e.g. if the latest Stat in the sqlite db is:
    #   { 19.99, 10, 10.99, 5, 2023-01-01T00:00:00Z }  (max_buy_price, num_buys, max_sell_price, num_sells, timestamp)
    #
    #   and 4 new buy events are received with a max price of 99.99, the next stat written to stats must be similar to:
    #   { 99.99, 14, 10.99, 5, 2023-01-01T00:00:05Z }
    #
    #   if 10 more sell events were also received, but the max price of all events did not exceed 10.99, the stat would
    #   then look something like:
    #   { 99.99, 14, 10.99, 15, 2023-01-01T00:00:05Z }

    # TODO create a timestamp (e.g. datetime.datetime.now().strftime('...'))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    # TODO create a last_updated variable that is initially assigned the timestamp, i.e. last_updated = timestamp
    last_updated = timestamp

    # TODO log beginning of processing
    logger.debug(f"Beginning processing: {timestamp}")

    # TODO create a session
    session = DB_SESSION()

    # TODO read latest record from stats.sqlite (ordered by last_updated)

    result = get_latest_stats()
    result = result[0]

    # TODO if result is not empty, convert result to a dict, read the last_updated property and store it in a variable named last_updated
    # if result does not exist, create a dict with default keys and values, and store it in the result variable
    last_updated = result["last_updated"]

    headers = {"Content-Type": "application/json"}

    # TODO call the /buy GET endpoint of storage, passing last_updated
    buy_response = requests.get(
        f"http://34.130.75.254/buy?timestamp={last_updated}", headers=headers
    )
    # TODO convert result to a json object, loop through and calculate max_buy_price of all recent records
    buy_response = buy_response.json()

    buy_price_total = 0
    num_buys_total = 0

    for items in buy_response:
        if items["item_price"] > buy_price_total:
            buy_price_total = items["item_price"]
        num_buys_total += items["item_price"]

    # TODO call the /sell GET endpoint of storage, passing last_updated
    sell_response = requests.get(f"http://34.130.75.254/sell?timestamp={last_updated}")

    # TODO convert result to_2 a json object, loop through and calculate max_sell_price of all recent records
    sell_response = sell_response.json()

    sell_price_total = 0
    num_sells_total = 0

    for items in sell_response:
        if items["item_price"] > sell_price_total:
            sell_price_total = items["item_price"]
        num_sells_total += items["item_price"]

    # TODO write a new Stats record to stats.sqlite using timestamp and the statistics you just generated
    stats = Stats(
        buy_price_total, num_buys_total, sell_price_total, num_sells_total, last_updated
    )

    # TODO add, commit and optionally close the session
    session.add(stats)
    session.commit()
    session.close()

    return NoContent, 201


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, "interval", seconds=app_config["period"])
    sched.start()


app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api(
    "openapi.yml",
    base_path="/Processing",
    strict_validation=True,
    validate_responses=True,
)

with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger("basic")

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, use_reloader=False)
