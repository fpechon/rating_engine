# %%
from decimal import Decimal

import numpy as np
import pandas as pd

from engine.fingerprint import tariff_hash
from engine.graph import TariffGraph
from engine.loader import TariffLoader
from engine.tables import load_exact_table, load_range_table
from sandbox.simulate import price_dataframe, price_with_breakdown
from tools.visualize import visualize_graph

tables = {
    "driver_age_factor": load_range_table(
        "tariffs/motor_private/2024_09/tables/driver_age_factor.csv",
        default=Decimal(3.0),
    ),
    "vehicle_brand_category": load_exact_table(
        "tariffs/motor_private/2024_09/tables/vehicle_brand_category.csv", key_type=str
    ),
    "vehicle_brand_coefs": load_exact_table(
        "tariffs/motor_private/2024_09/tables/vehicle_brand_coefs.csv", key_type=int
    ),
    "zoning": load_exact_table(
        "tariffs/motor_private/2024_09/tables/zoning.csv",
        key_type=str,
        key_column="neighbourhood_id",
        value_column="zone",
    ),
    "zoning_coefs": load_exact_table(
        "tariffs/motor_private/2024_09/tables/zoning_coefs.csv",
        key_type=int,
    ),
}

loader = TariffLoader(tables=tables)
nodes = loader.load("tariffs/motor_private/2024_09/tariff.yaml")
graph = TariffGraph(nodes)

context = {
    "driver_age": 41,
    "density": 502,
    "brand": "BMW",
    "neighbourhood_id": "19581",
}
result = graph.evaluate("total_premium", context, trace=None)
result
# %%
dot = visualize_graph(graph)
dot


# %%
# Compute prices on a dataframe
n = 100000
df = pd.DataFrame(
    {
        "driver_age": np.random.randint(18, 100, n),
        "density": np.random.randint(4, 2000, n),
        "brand": "Audi",
        "neighbourhood_id": "19582",
    }
)

df["premium"] = price_dataframe(df, graph, "total_premium")
df

# %%
price_with_breakdown(df, graph, "total_premium")
