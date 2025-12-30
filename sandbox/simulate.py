import pandas as pd


def price_dataframe(df, graph, root):
    premiums = []

    for _, row in df.iterrows():
        context = row.to_dict()
        premium = graph.evaluate(root, context)
        premiums.append(premium)

    return pd.Series(premiums, index=df.index)


def price_with_breakdown(df, graph, root):
    rows = []

    for _, row in df.iterrows():
        context = row.to_dict()
        cache = graph.evaluate(root, context, trace={})
        rows.append(cache)

    return pd.DataFrame(rows)
