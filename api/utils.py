from .models import Chart, DataSource, DataSet, Operation, IntegrationAuth
from providers.models import Provider

NON_AUTH_PROVIDERS = ['stock market']

def clone_chart(chart_id, request, is_published, tokens):

    chart_to_clone = Chart.objects.get(pk=chart_id)

    datasources_tobe_cloned = chart_to_clone.datasource_set.all()
    datasets_tobe_cloned = chart_to_clone.dataset_set.all()

    datasource_mapper = {}

    # Check that we have a token for every datasource to be cloned
    if tokens is not None:
        for datasource in datasources_tobe_cloned:
            if datasource.provider not in tokens and datasource.provider not in NON_AUTH_PROVIDERS:
                raise ValueError('You appear to not be connected to the ' + datasource.provider + ' provider.')

    # Clone chart
    cloned_chart = Chart(
        name = chart_to_clone.name,
        chart_type = chart_to_clone.chart_type,
        series_type = chart_to_clone.series_type,
        background_color = chart_to_clone.background_color,
        color = chart_to_clone.color,
        color_range = chart_to_clone.color_range,
        y_axis_title = chart_to_clone.y_axis_title,
        x_axis_title = chart_to_clone.x_axis_title,
        x_axis_enabled = chart_to_clone.x_axis_enabled,
        is_published = is_published,
        user = request.user,
    )
    cloned_chart.save()

    for datasource in datasources_tobe_cloned:

        cloned_datasource = DataSource(
            name = datasource.name,
            chart = cloned_chart,
            provider = '',
            resource = datasource.resource,
            params = datasource.params,
            swagger_url = datasource.data_provider.swagger_url,
            user = request.user,
        )

        cloned_datasource.save()

        datasource_mapper[datasource.pk] = cloned_datasource

    for dataset in datasets_tobe_cloned:

        # Clone each dataset
        cloned_dataset = DataSet(
            name = dataset.name,
            chart = cloned_chart,
            y_axis_enabled = dataset.y_axis_enabled,
            y_axis_is_opposite = dataset.y_axis_is_opposite,
            y_axis_title = dataset.y_axis_title,
            y_axis_id = dataset.y_axis_id,
            color = dataset.color,
            user = request.user,
        )
        cloned_dataset.save()

        for source in dataset.sources.all():
            cloned_dataset.sources.add(datasource_mapper[source.pk])
            cloned_dataset.save()

        # For every dataset find its operations
        operations_tobe_cloned = dataset.operation_set.all()
        for operation in operations_tobe_cloned:

            # Clone each operation
            cloned_operation = Operation(
                name = operation.name,
                dataset = cloned_dataset,
                root_function = operation.root_function,
                ast = operation.ast,
                sort_order = operation.sort_order,
                user = request.user,
            )
            cloned_operation.save()

    return cloned_chart
