import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-insurance',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './insurance.html',
  styleUrl: './insurance.scss',
})
export class Insurance {
  
  // Current Insurance
  insurance = {
    provider: "HDFC Ergo",
    policyNo: "POL-45233621",
    expiresOn: "2026-08-12",
    status: "active"
  };

  // Plans
  plans = [
    { name: "Basic Cover", price: 1500, duration: "1 Year" },
    { name: "Standard Cover", price: 2300, duration: "1 Year" },
    { name: "Premium Cover", price: 3500, duration: "2 Years" }
  ];

  selectedPlan: any = null;

  selectPlan(plan: any) {
    this.selectedPlan = plan;
  }
}