from .models import Chart, DataSource, DataSet, Operation, IntegrationAuth

def clone_chart(chart_id, request, is_published, tokens):
    # Get the chart
    chart_to_clone = Chart.objects.get(pk=chart_id)

    # Get all its datasources
    datasources_tobe_cloned = chart_to_clone.datasource_set.all()

    # Check that we have a token for every datasource to be cloned
    if tokens is not None:
        for datasource in datasources_tobe_cloned:
            if datasource.provider not in tokens:
                raise ValueError('You appear to not be connected to the ' + datasource.provider + ' provider.')

    # Clone chart
    cloned_chart = Chart(
        name = chart_to_clone.name,
        chart_type = chart_to_clone.chart_type,
        series_type = chart_to_clone.series_type,
        background_color = chart_to_clone.background_color,
        x_axis_title = chart_to_clone.x_axis_title,
        x_axis_enabled = chart_to_clone.x_axis_enabled,
        is_published = is_published,
        user = request.user,
    )
    cloned_chart.save()

    for datasource in datasources_tobe_cloned:
        # For every data source create a clone
        integration = None
        if tokens is not None:
            integration_key = tokens[datasource.provider]['key']
            integration = IntegrationAuth.objects.get(key=integration_key)

        cloned_datasource = DataSource(
            name = datasource.name,
            chart = cloned_chart,
            provider = datasource.provider,
            resource = datasource.resource,
            params = datasource.params,
            integration_auth = integration,
            user = request.user,
        )
        cloned_datasource.save()

        # For every data source find its datasets
        datasets_tobe_cloned = datasource.dataset_set.all()
        for dataset in datasets_tobe_cloned:
            # Clone each dataset
            cloned_dataset = DataSet(
                name = dataset.name,
                chart = cloned_chart,
                data_source = cloned_datasource,
                y_axis_enabled = dataset.y_axis_enabled,
                y_axis_is_opposite = dataset.y_axis_is_opposite,
                y_axis_title = dataset.y_axis_title,
                y_axis_id = dataset.y_axis_id,
                color = dataset.color,
                data = '[]',
                user = request.user,
            )
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
