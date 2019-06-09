from django.db import models
from django.contrib.postgres.fields import JSONField

class Chart(models.Model):
    name = models.CharField(max_length=100)
    chart_type = models.CharField(max_length=100)
    series_type = models.CharField(max_length=100)

    def __str__(self):
        return str(self.name)

class DataSource(models.Model):
    name = models.CharField(max_length=100)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    provider = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)

    def __str__(self):
        return str(self.name)

class DataSet(models.Model):
    name = models.CharField(max_length=100)
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    y_axis_id = models.CharField(max_length=100)
    data = JSONField()

    def __str__(self):
        return str(self.name)

class Operation(models.Model):
    name = models.CharField(max_length=100)
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE)
    root_function = models.CharField(max_length=100)
    ast = JSONField()