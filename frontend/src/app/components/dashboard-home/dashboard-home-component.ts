import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-dashboard-home-component',
  standalone: true,
  imports: [RouterOutlet, RouterLink, CommonModule],
  templateUrl: './dashboard-home-component.html',
  styleUrl: './dashboard-home-component.scss',
})
export class DashboardHomeComponent {

  constructor(private router: Router, private auth: AuthService) {}

  logout() {
    this.auth.logout();   // clear token
    this.router.navigate(['/']); // go to login
  }

}
