import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-insurance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './insurance.html',
  styleUrl: './insurance.scss',
})
export class Insurance implements OnInit {
  vehicles: any[] = [];
  selectedVehicleCode = '';
  insurance: any = null;
  plans: any[] = [];
  selectedPlan: any = null;

  loadingInsurance = false;
  loadingPlans = true;
  error = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listVehicles().subscribe({
      next: (list) => (this.vehicles = list),
      error: () => (this.error = 'Failed to load vehicles'),
    });

    this.api.getInsurancePlans().subscribe({
      next: (res) => {
        this.plans = res.plans ?? [];
        this.loadingPlans = false;
      },
      error: () => {
        this.loadingPlans = false;
      },
    });
  }

  onVehicleChange(): void {
    if (!this.selectedVehicleCode) return;
    this.loadingInsurance = true;
    this.insurance = null;

    this.api.getVehicleInsurance(this.selectedVehicleCode).subscribe({
      next: (res) => {
        this.insurance = res.found ? res : null;
        this.loadingInsurance = false;
      },
      error: () => {
        this.loadingInsurance = false;
      },
    });
  }

  selectPlan(plan: any): void {
    this.selectedPlan = plan;
  }

  daysLeftPercent(): number {
    if (!this.insurance?.days_left) return 0;
    return Math.min(100, Math.round((this.insurance.days_left / 365) * 100));
  }
}
