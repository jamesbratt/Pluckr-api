from django.core.exceptions import ObjectDoesNotExist
from .models import Chart, DataSource, DataSet, Operation, IntegrationAuth
from providers.models import Provider
from providers.utils import Swagger

NON_AUTH_PROVIDERS = ['stock market']

def clone_chart(chart_id, request, is_published, source_providers):

    chart_to_clone = Chart.objects.get(pk=chart_id)

    datasources_tobe_cloned = chart_to_clone.datasource_set.all()
    datasets_tobe_cloned = chart_to_clone.dataset_set.all()

    if source_providers is not None:
        if source_providers.__len__() != datasets_tobe_cloned.__len__():
            raise ValueError("You must select a data provider for every data source.")

    datasource_mapper = {}

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

        swagger_info = datasource.swagger_info
        if is_published is True:
            swagger_url = datasource.data_provider.swagger_url
            swagger_info = Swagger(swagger_url).extract_info()

        cloned_datasource = DataSource(
            name=datasource.name,
            chart=cloned_chart,
            provider='',
            resource=datasource.resource,
            params=datasource.params,
            swagger_info=swagger_info,
            user=request.user,
        )

        if source_providers is not None and is_published is False:
            provider_id = source_providers[str(datasource.id)]

            try:
                provider = Provider.objects.get(pk=provider_id)
                cloned_datasource.data_provider = provider
            except ObjectDoesNotExist:
                cloned_chart.delete()
                raise ValueError(
                    "The data provider that you have chosen to connect to the data source titled "
                    + datasource.name + " does not exist."
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
