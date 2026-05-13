from django.db import models

# Create your models here.
class Members(models.Model): 
    Student_ID = models.CharField(max_length=45, primary_key=True)
    Name = models.CharField(max_length=45)
    YearOfStudy = models.IntegerField()
    TeamName = models.CharField(max_length=45)
    def __str__(self):
        return self.Student_ID 
    

class Duration(models.Model):
    Student_ID = models.ForeignKey(Members, on_delete=models.CASCADE)
    EntryExit_ID = models.AutoField(primary_key=True)
    EntryTime = models.DateTimeField(null=True)
    ExitTime = models.DateTimeField(null=True, blank=True)
    TimeSpent = models.DurationField(null=True, blank=True)
    def __str__(self):
        return f"{self.Student_ID} - {self.EntryExit_ID}"