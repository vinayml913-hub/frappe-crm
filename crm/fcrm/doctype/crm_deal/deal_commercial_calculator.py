import frappe


@frappe.whitelist()
def get_deal_commercial_calculator_script():
	return """// CRM Deal Commercial Calculator
//
// Mirrors crm_deal.py's calculate_financials() EXACTLY, so the Proposed/
// Landing totals, GST-adjusted display totals, and Gross Profit update
// live in the browser as the user types - in both the Create Deal
// (Quick Entry) modal and the full Deal form/sidebar, since both use the
// same generic FieldLayout -> triggerOnChange() -> this[fieldname]()
// mechanism this script hooks into.
//
// The Python calculate_financials() on the server remains the source of
// truth and runs again on save/validate - this script only gives instant
// visual feedback before that save happens. If you ever change the
// formula, change it in BOTH places.

function round2(value) {
	return Math.round((Number(value) || 0) * 100) / 100
}

// Trainer Cost = Commercial x Days (or Hours), depending on Costing Type.
function costLeg(commercial, costingType, noOfDays, noOfHours) {
	commercial = Number(commercial) || 0
	if (costingType === 'Per Day') return commercial * (Number(noOfDays) || 0)
	if (costingType === 'Per Hour') return commercial * (Number(noOfHours) || 0)
	return commercial
}

// Lab Total = Cost x Days/Hours, unless Costing Type is a flat
// "Total Lab Costing" lump sum, in which case Cost is used as-is.
function labLeg(cost, costingType, noOfDays, noOfHours) {
	cost = Number(cost) || 0
	if (costingType === 'Per Day') return cost * (Number(noOfDays) || 0)
	if (costingType === 'Per Hour') return cost * (Number(noOfHours) || 0)
	return cost
}

class CRMDeal {
	// Run once when the form loads/re-renders, so totals are already
	// correct when opening an existing Deal for editing - not just after
	// the next field change.
	refresh() {
		this.calculate()
	}

	// Proposed Cost (Quoted) inputs
	proposed_trainer_commercial() { this.calculate() }
	proposed_trainer_costing_type() { this.calculate() }
	proposed_trainer_no_of_days() { this.calculate() }
	proposed_trainer_no_of_hours() { this.calculate() }
	proposed_lab_cost() { this.calculate() }
	proposed_lab_costing_type() { this.calculate() }
	proposed_lab_no_of_days() { this.calculate() }
	proposed_lab_no_of_hours() { this.calculate() }
	proposed_certification_cost() { this.calculate() }
	proposed_misc_expense() { this.calculate() }
	// Flipping the override off snaps straight back to the auto value.
	proposed_total_override() { this.calculate() }

	// Landing Cost (Expenses) inputs
	landing_trainer_commercial() { this.calculate() }
	landing_trainer_costing_type() { this.calculate() }
	landing_trainer_no_of_days() { this.calculate() }
	landing_trainer_no_of_hours() { this.calculate() }
	landing_lab_cost() { this.calculate() }
	landing_lab_costing_type() { this.calculate() }
	landing_lab_no_of_days() { this.calculate() }
	landing_lab_no_of_hours() { this.calculate() }
	landing_certification_cost() { this.calculate() }
	landing_misc_expense() { this.calculate() }
	landing_total_override() { this.calculate() }

	// GST (display-only toggle - never affects Gross Profit)
	gst_type() { this.calculate() }
	gst_percentage() { this.calculate() }

	calculate() {
		const d = this.doc

		const proposedTrainerCost = costLeg(
			d.proposed_trainer_commercial,
			d.proposed_trainer_costing_type,
			d.proposed_trainer_no_of_days,
			d.proposed_trainer_no_of_hours,
		)
		const proposedLabTotal = labLeg(
			d.proposed_lab_cost,
			d.proposed_lab_costing_type,
			d.proposed_lab_no_of_days,
			d.proposed_lab_no_of_hours,
		)
		// Proposed Total: auto-calculated UNLESS the manual override is
		// checked, in which case whatever the user typed is left alone.
		const proposedTotal = d.proposed_total_override
			? Number(d.proposed_total) || 0
			: proposedTrainerCost +
				proposedLabTotal +
				(Number(d.proposed_certification_cost) || 0) +
				(Number(d.proposed_misc_expense) || 0)

		const landingTrainerCost = costLeg(
			d.landing_trainer_commercial,
			d.landing_trainer_costing_type,
			d.landing_trainer_no_of_days,
			d.landing_trainer_no_of_hours,
		)
		const landingLabTotal = labLeg(
			d.landing_lab_cost,
			d.landing_lab_costing_type,
			d.landing_lab_no_of_days,
			d.landing_lab_no_of_hours,
		)
		// Landing Total: same manual-override rule as Proposed Total above.
		const landingTotal = d.landing_total_override
			? Number(d.landing_total) || 0
			: landingTrainerCost +
				landingLabTotal +
				(Number(d.landing_certification_cost) || 0) +
				(Number(d.landing_misc_expense) || 0)

		// GST only affects the DISPLAYED totals, never Gross Profit.
		const gstPct = Number(d.gst_percentage) || 18
		let proposedTotalWithGst = proposedTotal
		let landingTotalWithGst = landingTotal
		if (d.gst_type === 'Including GST') {
			proposedTotalWithGst = proposedTotal * (1 + gstPct / 100)
			landingTotalWithGst = landingTotal * (1 + gstPct / 100)
		}

		// Gross Profit - always pre-GST, feeds the dashboard/target.
		const grossProfit = proposedTotal - landingTotal
		const grossProfitPct = proposedTotal ? (grossProfit / proposedTotal) * 100 : 0

		this.doc.proposed_trainer_cost = round2(proposedTrainerCost)
		this.doc.proposed_lab_total = round2(proposedLabTotal)
		this.doc.proposed_total = round2(proposedTotal)

		this.doc.landing_trainer_cost = round2(landingTrainerCost)
		this.doc.landing_lab_total = round2(landingLabTotal)
		this.doc.landing_total = round2(landingTotal)

		this.doc.proposed_total_with_gst = round2(proposedTotalWithGst)
		this.doc.landing_total_with_gst = round2(landingTotalWithGst)

		this.doc.gross_profit = round2(grossProfit)
		this.doc.gross_profit_pct = round2(grossProfitPct)
	}
}
"""
