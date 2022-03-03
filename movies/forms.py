from django import forms
from .models import Rank


class RankForm(forms.ModelForm):
    
    class Meta:
        model = Rank
        fields = ['rank', 'content']