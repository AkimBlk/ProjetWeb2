from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse

class Post(models.Model):

    # createur de l'agent
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agents') 
    
    # info de l'agent
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # parametre de l'ia
    pre_prompt = models.TextField(default="You are an ai who help user.")
    avatar = models.ImageField(default='default.jpg', upload_to='avatar_pics') 
    cooldown = models.IntegerField(default=5)#seconde

    model_choices = [
        ('LOCAL', 'Local'),
        ('API', 'API'),
    ]
    model_type = models.CharField(max_length=10, choices=model_choices, default='API')

    #conversation / historique
    conversation = models.TextField(default="", blank=True) #blank=True pour pouvoir creer un agent sans historique directement, pour que la conversation soit vide

    # date pour les stats + level d'activité
    date_created = models.DateTimeField(default=timezone.now)
    last_message_date = models.DateTimeField(auto_now=True) # maj auto a chaque object.save()
    interaction_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        # Renvoie vers la page de chat
        return reverse('post-detail', kwargs={'pk':self.pk})

class PostCooldown(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_interaction = models.DateTimeField(auto_now=True)# maj auto a chaque object.save()

    class Meta:
        unique_together = ("post", "user") #empeche les doublon user , post